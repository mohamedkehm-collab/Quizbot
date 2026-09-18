"""
Regroupe les catégories fines existantes (ex. "Histoire / Antiquité",
"Sur les traités antique", "Botanique / Gastronomie") en thèmes larges
et lisibles (ex. "histoire", "mythologie", "sport") utilisables avec
!quiz <theme>.

La colonne d'origine `categorie` est conservée telle quelle (elle sert
pour l'affichage). Une nouvelle colonne `theme` est ajoutée/mise à jour.

Relançable à volonté (idempotent) — utile après un !ajouter ou un nouvel
import pour reclasser les nouvelles catégories.
"""
import sqlite3
import os
import re
import unicodedata

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "questions.db")


def normalize(text: str) -> str:
    if text is None:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Ordre de priorité : la première règle dont un mot-clé apparaît dans la
# catégorie normalisée l'emporte. Les thèmes les plus "spécifiques"
# passent avant les thèmes génériques (ex. "mythologie" avant "histoire").
REGLES = [
    ("mythologie", ["mytholog", "yggdrasil", "divinite", "dieu grec", "asgard"]),
    ("astronomie", ["astronom", "spatial", "planete", "aventure spatiale"]),
    ("litterature", ["litterature", "litterair", "poesie", "poete", "roman",
                      "conte", "ecrivain", "theatre", "au voleur"]),
    ("mythologie", ["conte fantastique"]),
    ("religion", ["religio", "saint patron", "les saints", "culte", "bible",
                   "protestantisme", "dignitaires et chefs religieux", "opera / art"]),
    ("histoire", ["histoire", "bataille", "traite", "guerre", "tsars", "siege",
                  "occupe", "antiquite", "empire", "revolution", "royaut",
                  "royales", "monarch", "couronnement"]),
    ("geopolitique", ["geopolitique", "geographie histoire", "geographie / histoire",
                       "histoire et geographie", "histoire geographie"]),
    ("sport", ["sport", "athletisme", "football", "tennis", " jo ", "jo d ete",
               "jeux olympiques", "golf", "catch", "trophee", "attaquant",
               "entraineur", "selectionneur", "champion", "usain bolt"]),
    ("cinema", ["cinema", "film", "dessin anime", "serie tv", "series tv",
                "series tele", "television", "televisi", "maman j ai rate"]),
    ("musique", ["musique", "opera", "chanson", "compositeur"]),
    ("geographie", ["geographie", "ville", "pays", "capitale", "continent",
                     "region", "metropole", "grandes villes", "grands parcs",
                     "taxis du monde", "iles des regions"]),
    ("sciences", ["science", "technique", "technologie", "informatique",
                   "mathematique", "physique", "chimie", "biologie",
                   "invention", "internet", "reseaux"]),
    ("art", ["art", "peintr", "sculpture", "artiste", "moma", "ceramique",
             "couleurs", "architecture", "tableau"]),
    ("animaux", ["animal", "animaux", "zoologie", "chien", "oiseau", "rapace",
                 "serpent"]),
    ("nature", ["botaniq", "environnement", "nature"]),
    ("gastronomie", ["gastronomie", "cuisine", "sucre sale", "fruits dans",
                      "lettre t en gastronomie", "banane"]),
    ("medecine", ["medecine", "anatomie", "sante", "dentaire", "pharmacie",
                   "ophtalmologie", "ventre", "tronc en anatomie"]),
    ("philosophie", ["philosophie", "rhetorique", "psychologie"]),
    ("politique", ["politique", "droit ", "economie", "finance", "marketing",
                    "entreprise", "actualite"]),
    ("mode", ["mode", "costume", "couture", "bague", "fil en couture"]),
    ("langue", ["langue", "linguistique", "expression", "mots finissant",
                "adjectif qualificatif", "vocabulaire"]),
    ("societe", ["culture / ", "education", "divertissement", "jeux video",
                 "bande dessinee", "bandes dessinees", "bd", "loisirs",
                 "conference"]),
]

FALLBACK_EXACT = {
    "sur les lois et principes": "sciences",
    "romans policiers": "litterature",
    "robinson crusoe": "litterature",
    "les medias dans les romans": "litterature",
    "les sorciers et les sorcieres": "mythologie",
    "les groupes dans les tableaux": "art",
    "le canada": "geographie",
    "le cheval en france": "animaux",
    "la culture coreenne": "societe",
    "exploration": "histoire",
    "travail": "societe",
    "prenom culture": "langue",
    "danse": "art",
    "chez le dentiste": "medecine",
    "termes medicaux et langage courant": "medecine",
}


def choisir_theme(categorie: str) -> str:
    norm = normalize(categorie)
    if norm in FALLBACK_EXACT:
        return FALLBACK_EXACT[norm]
    if norm.startswith("culture generale"):
        return "generale"
    for theme, mots_cles in REGLES:
        for mot in mots_cles:
            if mot.strip() and mot.strip() in norm:
                return theme
    return "divers"


def main():
    conn = sqlite3.connect(DB_PATH)
    colonnes = [r[1] for r in conn.execute("PRAGMA table_info(questions)")]
    if "theme" not in colonnes:
        conn.execute("ALTER TABLE questions ADD COLUMN theme TEXT")
        conn.commit()

    cats = [r[0] for r in conn.execute("SELECT DISTINCT categorie FROM questions").fetchall()]
    mapping = {c: choisir_theme(c) for c in cats}

    for cat, theme in mapping.items():
        conn.execute("UPDATE questions SET theme = ? WHERE categorie = ?", (theme, cat))
    conn.commit()

    print("Répartition par thème :")
    for row in conn.execute("SELECT theme, COUNT(*) as n FROM questions GROUP BY theme ORDER BY n DESC"):
        print(f"  {row[0]:15s} {row[1]}")

    print("\nCatégories tombées dans 'divers' (à vérifier) :")
    for row in conn.execute(
        "SELECT categorie, COUNT(*) FROM questions WHERE theme='divers' GROUP BY categorie ORDER BY COUNT(*) DESC"
    ):
        print(f"  {row[0]!r} -> {row[1]}")

    conn.close()


if __name__ == "__main__":
    main()
