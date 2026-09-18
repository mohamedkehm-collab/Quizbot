# Bot Discord — Quiz de culture générale

Ta base est déjà prête : **8241 questions** importées depuis tes fichiers
(mythologies, traités antiques, astronomie, littérature x2, batailles, lois
et principes, mythologie nordique, et ton fichier `questions.xlsx`), stockées
dans `data/questions.db`.

## Installation et hébergement (depuis un iPhone, gratuit, sans ordinateur)

Un bot Discord doit tourner **en continu** ; ça ne peut pas se faire sur
l'iPhone lui-même. On va l'héberger gratuitement sur **Render**, en pilotant
tout depuis Safari et l'app **Fichiers**. Trois étapes : mettre le code sur
GitHub, le brancher à Render, puis empêcher Render de s'endormir avec
UptimeRobot.

### Étape 1 — Créer le bot Discord et récupérer le token

1. Va sur https://discord.com/developers/applications (dans Safari) →
   **New Application**, donne-lui un nom.
2. Onglet **Bot** → active **MESSAGE CONTENT INTENT** (obligatoire).
3. **Reset Token** → copie le token (garde-le, tu en auras besoin à l'étape 3).
4. Onglet **OAuth2 → URL Generator** : coche `bot`, puis dans les
   permissions coche `Send Messages`, `Read Message History`, `Embed Links`.
   Ouvre l'URL générée en bas de page pour ajouter le bot à ton serveur.

### Étape 2 — Mettre le projet sur GitHub

1. Dézippe `quizbot.zip` : dans l'app **Fichiers**, appuie sur le fichier
   zip → "Décompresser". Tu obtiens un dossier `quizbot` avec tous les
   fichiers dedans.
2. Crée un compte sur https://github.com si tu n'en as pas.
3. En haut à droite → **+** → **New repository**. Nomme-le `quizbot`,
   laisse-le en **Private**, ne coche aucune case d'initialisation → **Create**.
4. Sur la page du repo vide, appuie sur **uploading an existing file**.
5. Appuie sur "choose your files", sélectionne **tous les fichiers** à
   l'intérieur du dossier `quizbot` décompressé (bot.py, import_data.py,
   assign_themes.py, requirements.txt, Procfile, README.md, .env.example,
   et le sous-dossier `data` avec `questions.db` dedans — refais l'upload
   une deuxième fois pour le contenu du dossier `data` si Safari ne prend
   pas les dossiers d'un coup). Commit.

⚠️ Ne mets **jamais** ton token Discord dans un fichier uploadé sur GitHub
(même privé) — il se configure à l'étape suivante, séparément.

### Étape 3 — Déployer sur Render

1. Crée un compte sur https://render.com (tu peux t'inscrire avec ton
   compte GitHub, c'est le plus simple).
2. **New +** → **Web Service**.
3. Connecte ton repo GitHub `quizbot` → **Connect**.
4. Renseigne :
   - **Name** : `quizbot` (ou ce que tu veux)
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python3 bot.py`
   - **Instance Type** : **Free**
5. Descends à **Environment Variables** → **Add Environment Variable** :
   - Key : `DISCORD_TOKEN`
   - Value : *(colle ton token Discord de l'étape 1)*
6. **Create Web Service**. Le premier déploiement prend quelques minutes —
   suis les logs affichés à l'écran. Une fois que tu vois `Connecté en tant
   que...` dans les logs, le bot est en ligne. Note l'URL affichée en haut
   (ex. `https://quizbot-xxxx.onrender.com`), elle sert juste à l'étape 4.

### Étape 4 — Empêcher Render de s'endormir

Le plan gratuit de Render met le service en veille après 15 minutes sans
requête HTTP (le bot Discord, lui, resterait connecté un moment mais finira
coupé quand Render suspend le processus). **UptimeRobot** va simplement
visiter ton URL Render toutes les 5 minutes pour le garder éveillé,
gratuitement :

1. Crée un compte sur https://uptimerobot.com (gratuit).
2. **+ Add New Monitor** → Monitor Type : **HTTP(s)**.
3. Colle l'URL Render de l'étape 3 (celle en `.onrender.com`).
4. Intervalle : 5 minutes → **Create Monitor**.

C'est tout : le bot doit maintenant rester en ligne 24h/24, gratuitement.

**Limites à connaître avec ce montage gratuit** : Render free offre 750h
d'instance par mois (~31 jours) — largement suffisant pour un seul bot,
mais évite de laisser tourner d'autres services gratuits sur le même compte
en même temps. De très rares utilisateurs signalent des ralentissements
occasionnels dus à la façon dont Render achemine le trafic vers Discord ; si
tu vois le bot devenir capricieux, Railway (~5$/mois) est l'alternative la
plus fiable, avec la même méthode d'installation (sans les étapes 4 et le
Procfile).

### Mettre à jour le bot plus tard

Modifie les fichiers directement sur GitHub (bouton crayon ✏️ sur chaque
fichier, éditable depuis Safari), commit — Render redéploie automatiquement
à chaque commit sur le repo.

---

## Utilisation en local (si un jour tu as un ordinateur sous la main)

```bash
pip install -r requirements.txt
cp .env.example .env   # puis colle ton token dedans
python3 bot.py
```

## Commandes

| Commande | Effet |
|---|---|
| `!quiz` | Pose une question au hasard, tous thèmes confondus. Tu as **12 secondes** pour répondre directement dans le salon. |
| `!quiz mythologie` | Pose une question du thème **mythologie** |
| `!quiz histoire25` | Lance une **série de 25 questions** du thème **histoire**, à la suite |
| `!quiz histoire 25` | Pareil (avec ou sans espace, comme tu veux) |
| `!quiz 10` | Série de 10 questions, tous thèmes confondus |
| `!themes` | Liste tous les thèmes disponibles et le nombre de questions dans chacun |
| `!ajouter Question \| Réponse \| Explication \| Thème` | Ajoute une question (explication et thème optionnels — thème "perso" par défaut) |
| `!stats` | Nombre de questions en base, questions posées, taux de réussite |
| `!arreter` | Arrête la série en cours (après la question active) |

### Les thèmes disponibles

`generale`, `histoire`, `litterature`, `mythologie`, `sciences`, `astronomie`,
`geographie`, `sport`, `cinema`, `medecine`, `art`, `animaux`, `religion`,
`musique`, `nature`, `langue`, `societe`, `mode`, `philosophie`, `politique`,
`geopolitique`, `gastronomie`, `divers`

(Tape `!themes` dans Discord pour voir le nombre exact de questions par
thème — la répartition peut évoluer si tu ajoutes des questions.)

Si tu tapes un thème qui n'existe pas, le bot retombe automatiquement sur
une recherche dans les catégories précises d'origine (ex. `!quiz Kadesh`
trouvera quand même les questions sur le Traité de Kadesh), et sinon te
liste les thèmes valides.

**Validation des réponses** : le bot ignore les majuscules, les accents, la
ponctuation, et tolère un article en trop devant la réponse (ex. répondre
"Hugo" ou "Victor Hugo" pour "Quel écrivain..." → *Victor Hugo* fonctionne
tous les deux). Il tolère aussi les petites fautes de frappe grâce à une
comparaison de similarité — mais une réponse trop différente sera comptée
comme fausse.

## Ajouter davantage de questions depuis un fichier

Si tu obtiens de nouveaux fichiers `.docx` (tableau à 3 colonnes : Question |
Réponse | Explication) ou `.xlsx` (colonnes Categorie | Question |
BonneReponse), tu peux les importer sans dupliquer ce qui existe déjà :

```bash
python3 import_data.py chemin/vers/nouveau_fichier.docx
python3 import_data.py chemin/vers/nouveau_fichier.xlsx
# ou pour tout un dossier d'un coup :
python3 import_data.py --dossier chemin/vers/dossier
```

Le thème est assigné automatiquement (`assign_themes.py`) d'après le nom de
la catégorie/du fichier. Si une nouvelle catégorie ne correspond à aucune
règle connue, elle tombe dans le thème `divers` — tu peux relancer
`python3 assign_themes.py` à tout moment pour reclasser toute la base (par
exemple après avoir ajusté les règles dans ce fichier).

Les questions ajoutées via `!ajouter` dans Discord vont dans la catégorie
**Perso** et le thème **perso** par défaut (sauf si tu précises un thème en
4e partie de la commande).

## Structure des fichiers

```
quizbot/
├── bot.py              # Le bot lui-même (+ mini-serveur web pour Render)
├── import_data.py       # Script d'import Word/Excel → base SQLite
├── assign_themes.py     # Classe les catégories précises en thèmes larges
├── requirements.txt
├── Procfile             # Indique à Render comment démarrer le bot
├── .env.example
├── README.md
└── data/
    └── questions.db      # Ta base, déjà remplie et déjà thématisée (8241 questions)
```
