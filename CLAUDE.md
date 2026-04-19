# CLAUDE.md — disnperfo

> Projet : Application web affichant les 5 meilleures ventes de figurines Disney Traditions
> Sources : amazon.com.be et cadeaucity.com
> Langue de l'application : Français

---

## 0) Langue

Communiquer en français avec l'utilisateur.
Code, commits, et noms de variables en anglais.
Interface utilisateur (frontend) en français.

---

## 1) Architecture

### Stack
- **Backend** : Python 3.11+ / FastAPI
- **Scraping Amazon** : Playwright (headless Chromium)
- **Scraping CadeauCity** : requests + BeautifulSoup4
- **Frontend** : HTML / CSS / JS (pas de framework)
- **Hébergement** : Render (gratuit) — URL : disnperfo.onrender.com

### Structure du projet
```
oncle_walt/
├── app/
│   ├── main.py              # FastAPI app + endpoints
│   ├── scrapers/
│   │   ├── amazon.py        # Scraper Amazon.com.be
│   │   └── cadeaucity.py    # Scraper CadeauCity
│   ├── models.py            # Modèles de données (Product)
│   └── cache.py             # Cache en mémoire des résultats
├── static/
│   ├── index.html           # Page principale
│   ├── style.css            # Styles
│   └── script.js            # Logique frontend
├── requirements.txt
├── Dockerfile
├── render.yaml
└── CLAUDE.md
```

---

## 2) Règles de fonctionnement

### Mode opératoire
- Plan mode uniquement pour décisions d'architecture ou changements risqués.
- Vérifier avant de marquer une tâche comme terminée.
- Après correction utilisateur : mettre à jour lessons.md.

### Sécurité
- Ne jamais leaker de secrets (clés API, mots de passe).
- Respecter les limites de scraping : max 1 requête toutes les 6h par source.

---

## 3) Git

Après toute modification de code :
1. git add des fichiers modifiés
2. git commit avec message descriptif
3. git push origin main

---

## 4) Exécuter le projet

```bash
# Installation
pip install -r requirements.txt
playwright install chromium

# Lancement local
uvicorn app.main:app --reload --port 8000
```

---

## 5) Conventions de code

- Python : snake_case, type hints, docstrings en anglais.
- Frontend : français pour tout texte visible par l'utilisateur.
- Pas de sur-ingénierie. Garder le code simple.

---

## 6) Imports

@lessons.md
