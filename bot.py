"""
Bot Discord d'entraînement à la culture générale.

Commandes :
  !quiz                  Pose une question au hasard, toutes catégories confondues
  !quiz mythologie       Pose une question du thème "mythologie"
  !quiz histoire25       Lance une série de 25 questions du thème "histoire"
  !quiz 10               Lance une série de 10 questions, toutes catégories
  !themes                Liste les thèmes disponibles et le nombre de questions
  !ajouter Q | R | E     Ajoute une question (E = explication, optionnelle)
  !stats                 Affiche tes statistiques personnelles
  !arreter               Arrête la série de questions en cours

Configuration : mets ton token dans un fichier .env (voir .env.example) sous la
clé DISCORD_TOKEN, ou exporte la variable d'environnement DISCORD_TOKEN.
"""
import os
import re
import sqlite3
import random
import unicodedata
import asyncio
import threading
from difflib import SequenceMatcher

import discord
from discord.ext import commands
from flask import Flask

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "questions.db")
TEMPS_REPONSE = 12  # secondes
SEUIL_SIMILARITE = 0.82  # tolérance aux fautes de frappe (0 à 1, 1 = exact)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Empêche deux questions actives en même temps dans le même salon
# channel_id -> {"stop": bool}
questions_actives = {}

MAX_SERIE = 50  # nombre max de questions dans une série (!quiz theme50)


def parse_quiz_args(raw: str):
    """Extrait (theme, nombre_de_questions) depuis l'argument de !quiz.
    Exemples : "mythologie" -> ("mythologie", 1)
               "histoire25" -> ("histoire", 25)
               "histoire 25" -> ("histoire", 25)
               "10" -> (None, 10)
               "" / None -> (None, 1)
    """
    if not raw:
        return None, 1
    raw = raw.strip()
    tokens = raw.split()
    count = 1
    if tokens and tokens[-1].isdigit():
        count = int(tokens.pop())
        raw = " ".join(tokens).strip()
    else:
        m = re.match(r"^(.*?)(\d+)$", raw)
        if m and m.group(1).strip():
            raw = m.group(1).strip()
            count = int(m.group(2))
    theme = raw if raw else None
    count = max(1, min(count, MAX_SERIE))
    return theme, count


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize(text: str) -> str:
    if text is None:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def reponse_correcte(donnee: str, attendue: str) -> bool:
    """Valide la réponse : match exact après normalisation, ou très proche
    (tolère les fautes de frappe / accents / articles en trop)."""
    d = normalize(donnee)
    a = normalize(attendue)
    if not d:
        return False
    if d == a:
        return True
    # Tolère "le/la/les/l'" en préfixe de la bonne réponse
    a_sans_article = re.sub(r"^(le |la |les |l |un |une |des )", "", a)
    if d == a_sans_article:
        return True
    # Tolère de ne donner qu'un mot significatif de la réponse
    # (ex. "Hugo" pour "Victor Hugo", "Vivaldi" pour "Antonio Vivaldi")
    mots = [m for m in a.split() if len(m) >= 4]
    if d in mots:
        return True
    # Similarité globale (fautes de frappe)
    ratio = SequenceMatcher(None, d, a).ratio()
    return ratio >= SEUIL_SIMILARITE


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} — prêt à faire réviser !")


def theme_existe(conn, theme: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM questions WHERE theme = ? LIMIT 1", (normalize(theme),)
    ).fetchone()
    return row is not None


def tirer_question(conn, theme: str):
    """Retourne une question au hasard, filtrée par thème si fourni.
    Cherche d'abord une correspondance exacte de thème, puis retombe sur
    une recherche partielle dans la catégorie précise (rétrocompatibilité)."""
    if not theme:
        return conn.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1").fetchone()

    theme_norm = normalize(theme)
    row = conn.execute(
        "SELECT * FROM questions WHERE theme = ? ORDER BY RANDOM() LIMIT 1", (theme_norm,)
    ).fetchone()
    if row is not None:
        return row
    return conn.execute(
        "SELECT * FROM questions WHERE categorie LIKE ? ORDER BY RANDOM() LIMIT 1",
        (f"%{theme}%",),
    ).fetchone()


async def poser_une_question(ctx, row) -> bool:
    """Pose une question, attend TEMPS_REPONSE secondes, valide la réponse.
    Retourne True si la personne a trouvé la bonne réponse."""
    channel_id = ctx.channel.id
    conn = get_conn()
    conn.execute("UPDATE questions SET fois_posee = fois_posee + 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title=f"❓ Question — {row['categorie']}",
        description=row["question"],
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Tu as {TEMPS_REPONSE} secondes...")
    await ctx.send(embed=embed)

    def check(m):
        return m.channel.id == channel_id and not m.author.bot

    trouve = False
    fin = asyncio.get_event_loop().time() + TEMPS_REPONSE
    try:
        while True:
            restant = fin - asyncio.get_event_loop().time()
            if restant <= 0:
                break
            msg = await bot.wait_for("message", timeout=restant, check=check)
            if msg.content.startswith("!"):
                continue  # ignore les autres commandes pendant qu'on attend
            if reponse_correcte(msg.content, row["reponse"]):
                trouve = True
                conn = get_conn()
                conn.execute("UPDATE questions SET fois_reussie = fois_reussie + 1 WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                await msg.reply(f"✅ Exact ! La réponse était **{row['reponse']}**.")
                break
    except asyncio.TimeoutError:
        pass

    if not trouve:
        texte = f"⏱️ Temps écoulé ! La réponse était **{row['reponse']}**."
        if row["explication"]:
            texte += f"\n*{row['explication']}*"
        await ctx.send(texte)
    elif row["explication"]:
        await ctx.send(f"💡 *{row['explication']}*")

    return trouve


@bot.command(
    name="quiz",
    help=(
        "Pose une question. Exemples : !quiz | !quiz mythologie | !quiz histoire25 "
        "(série de 25) | !quiz 10 (série de 10, tous thèmes)"
    ),
)
async def quiz(ctx, *, argument: str = None):
    channel_id = ctx.channel.id
    if channel_id in questions_actives:
        await ctx.send("Une série de questions est déjà en cours dans ce salon — réponds-y, ou tape `!arreter`.")
        return

    theme, nb_questions = parse_quiz_args(argument)

    conn = get_conn()
    if theme and not theme_existe(conn, theme):
        # pas un thème connu : on tente quand même une recherche par catégorie précise
        test = conn.execute(
            "SELECT 1 FROM questions WHERE categorie LIKE ? LIMIT 1", (f"%{theme}%",)
        ).fetchone()
        if test is None:
            themes = [r[0] for r in conn.execute(
                "SELECT DISTINCT theme FROM questions ORDER BY theme"
            ).fetchall()]
            conn.close()
            await ctx.send(
                f"Aucun thème ou catégorie ne correspond à « {theme} ».\n"
                f"Thèmes disponibles : {', '.join(themes)}"
            )
            return
    conn.close()

    questions_actives[channel_id] = {"stop": False}
    score = 0
    try:
        for i in range(nb_questions):
            if questions_actives[channel_id]["stop"]:
                break
            conn = get_conn()
            row = tirer_question(conn, theme)
            conn.close()
            if row is None:
                await ctx.send("Plus de questions disponibles pour ce thème.")
                break
            if nb_questions > 1:
                await ctx.send(f"**Question {i + 1}/{nb_questions}**")
            trouve = await poser_une_question(ctx, row)
            if trouve:
                score += 1
    finally:
        questions_actives.pop(channel_id, None)

    if nb_questions > 1:
        await ctx.send(f"🏁 Série terminée : **{score}/{nb_questions}** bonnes réponses.")


@bot.command(name="arreter", help="Arrête la série de questions en cours (après la question active).")
async def arreter(ctx):
    if ctx.channel.id in questions_actives:
        questions_actives[ctx.channel.id]["stop"] = True
        await ctx.send("D'accord, j'arrête la série après cette question.")
    else:
        await ctx.send("Aucune question en cours.")


@bot.command(name="themes", aliases=["categories"], help="Liste les thèmes disponibles et le nombre de questions.")
async def themes(ctx):
    conn = get_conn()
    rows = conn.execute(
        "SELECT theme, COUNT(*) as n FROM questions GROUP BY theme ORDER BY n DESC"
    ).fetchall()
    conn.close()
    if not rows:
        await ctx.send("La base est vide pour l'instant.")
        return
    texte = "\n".join(f"• **{r['theme']}** — {r['n']} questions" for r in rows)
    total = sum(r["n"] for r in rows)
    embed = discord.Embed(
        title=f"📚 Thèmes ({total} questions au total)",
        description=texte + "\n\nExemples : `!quiz mythologie`, `!quiz histoire25`, `!quiz 10`",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(
    name="ajouter",
    help="Ajoute une question : !ajouter Question | Réponse | Explication (optionnelle) | Thème (optionnel)",
)
async def ajouter(ctx, *, contenu: str):
    parties = [p.strip() for p in contenu.split("|")]
    if len(parties) < 2:
        await ctx.send("Format attendu : `!ajouter Question | Réponse | Explication (optionnelle) | Thème (optionnel)`")
        return
    question, reponse = parties[0], parties[1]
    explication = parties[2] if len(parties) > 2 else ""
    theme = normalize(parties[3]) if len(parties) > 3 and parties[3] else "perso"
    if not question or not reponse:
        await ctx.send("La question et la réponse ne peuvent pas être vides.")
        return

    conn = get_conn()
    q_norm = normalize(question)
    try:
        conn.execute(
            "INSERT INTO questions (categorie, question, reponse, explication, question_norm, theme) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Perso", question, reponse, explication, q_norm, theme),
        )
        conn.commit()
        await ctx.send(f"✅ Question ajoutée (thème **{theme}**) : *{question}*")
    except sqlite3.IntegrityError:
        await ctx.send("Cette question existe déjà dans la base.")
    finally:
        conn.close()


@bot.command(name="stats", help="Affiche tes statistiques globales sur la base.")
async def stats(ctx):
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as total, SUM(fois_posee) as posees, SUM(fois_reussie) as reussies FROM questions"
    ).fetchone()
    conn.close()
    posees = row["posees"] or 0
    reussies = row["reussies"] or 0
    taux = f"{(reussies / posees * 100):.0f}%" if posees else "—"
    embed = discord.Embed(title="📊 Statistiques", color=discord.Color.orange())
    embed.add_field(name="Questions en base", value=str(row["total"]), inline=True)
    embed.add_field(name="Questions posées", value=str(posees), inline=True)
    embed.add_field(name="Taux de réussite", value=taux, inline=True)
    await ctx.send(embed=embed)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit(
            "Erreur : la variable d'environnement DISCORD_TOKEN n'est pas définie.\n"
            "Crée un fichier .env (voir .env.example) ou exporte-la avant de lancer le bot."
        )

    # --- Mini-serveur web pour héberger sur Render (ou tout hébergeur qui
    # exige un port HTTP ouvert). Sans effet en local : n'écoute que si un
    # hébergeur fournit la variable PORT.
    port = os.environ.get("PORT")
    if port:
        web = Flask(__name__)

        @web.route("/")
        def accueil():
            return "Le bot de quiz est en ligne."

        def lancer_serveur_web():
            web.run(host="0.0.0.0", port=int(port))

        threading.Thread(target=lancer_serveur_web, daemon=True).start()

    bot.run(token)
