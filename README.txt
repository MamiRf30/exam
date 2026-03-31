Projet : Générateur de Quiz Intelligent (Flask + Groq)

1) Installation
- Créez un environnement virtuel (optionnel mais conseillé):
  python -m venv .venv
  source .venv/bin/activate      (Linux/Mac)
  .venv\Scripts\activate         (Windows)
- Installez les dépendances:
  pip install -r requirements.txt

2) Configuration de la clé API Groq
IMPORTANT: ne jamais écrire la clé en dur dans app.py.

Linux / Mac (bash):
  export GROQ_API_KEY="votre_cle_api_groq"
  export FLASK_SECRET_KEY="une_cle_flask_longue_et_aleatoire"

Windows PowerShell:
  setx GROQ_API_KEY "votre_cle_api_groq"
  setx FLASK_SECRET_KEY "une_cle_flask_longue_et_aleatoire"
  (puis redémarrer le terminal)

3) Lancer l'application
  python app.py

Puis ouvrez: http://127.0.0.1:5000

4) Contenu du rendu
- app.py
- templates/
- static/
- requirements.txt
- README.txt
- capture d'écran de l'application
