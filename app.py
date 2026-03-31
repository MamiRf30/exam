import json
import os
from typing import Any

from flask import Flask, flash, redirect, render_template, request, session, url_for
from groq import Groq

app = Flask(__name__)
# Clé utilisée par Flask pour signer la session (cookies).
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")


class QuizGenerationError(Exception):
    """Erreur personnalisée pour simplifier la gestion des erreurs métier."""


def validate_form_data(theme: str, num_questions: str, difficulty: str) -> tuple[str, int, str]:
    """Valide les entrées utilisateur et retourne des valeurs normalisées."""
    clean_theme = theme.strip()
    if not clean_theme:
        raise QuizGenerationError("Le thème ne peut pas être vide.")

    try:
        count = int(num_questions)
    except ValueError as exc:
        raise QuizGenerationError("Le nombre de questions doit être un entier.") from exc

    if count < 3 or count > 10:
        raise QuizGenerationError("Le nombre de questions doit être compris entre 3 et 10.")

    allowed_difficulties = {"Facile", "Moyen", "Difficile"}
    if difficulty not in allowed_difficulties:
        raise QuizGenerationError("Niveau de difficulté invalide.")

    return clean_theme, count, difficulty


def build_prompt(theme: str, count: int, difficulty: str) -> str:
    """Construit un prompt explicite pour forcer un JSON propre."""
    return f"""
Tu es un générateur de quiz pour des étudiants universitaires.
Génère exactement {count} questions QCM sur le thème: "{theme}".
Niveau de difficulté: {difficulty}.

Contraintes strictes:
- Chaque question contient exactement 4 options: A, B, C, D.
- Une seule bonne réponse par question.
- Retourne UNIQUEMENT du JSON valide, sans texte autour.
- Le JSON doit respecter exactement cette structure:
{{
  "questions": [
    {{
      "question": "Texte de la question",
      "options": {{
        "A": "option A",
        "B": "option B",
        "C": "option C",
        "D": "option D"
      }},
      "answer": "A"
    }}
  ]
}}
""".strip()


def extract_json_content(raw_content: str) -> dict[str, Any]:
    """Extrait le JSON même si le modèle renvoie des balises markdown."""
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise QuizGenerationError(
            "La réponse de l'IA n'est pas un JSON valide. Réessayez."
        ) from exc

    if "questions" not in parsed or not isinstance(parsed["questions"], list):
        raise QuizGenerationError("Le JSON retourné est mal structuré (clé 'questions' manquante).")

    for idx, question in enumerate(parsed["questions"], start=1):
        if not isinstance(question, dict):
            raise QuizGenerationError(f"La question #{idx} est invalide.")
        if not {"question", "options", "answer"}.issubset(question.keys()):
            raise QuizGenerationError(f"La structure de la question #{idx} est incomplète.")

        options = question["options"]
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            raise QuizGenerationError(f"Les options de la question #{idx} doivent être A, B, C, D.")

        if question["answer"] not in {"A", "B", "C", "D"}:
            raise QuizGenerationError(f"La bonne réponse de la question #{idx} est invalide.")

    return parsed


def generate_quiz_with_groq(theme: str, count: int, difficulty: str) -> list[dict[str, Any]]:
    """Appelle l'API Groq et retourne une liste de questions validée."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise QuizGenerationError(
            "La clé API Groq est absente. Configurez la variable d'environnement GROQ_API_KEY."
        )

    prompt = build_prompt(theme, count, difficulty)

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            messages=[
                {"role": "system", "content": "Tu réponds strictement en JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content or ""
    except Exception as exc:
        raise QuizGenerationError(
            "Erreur lors de l'appel à Groq (clé invalide, réseau indisponible ou quota dépassé)."
        ) from exc

    parsed = extract_json_content(content)
    questions = parsed["questions"]

    if len(questions) != count:
        raise QuizGenerationError(
            f"L'IA a retourné {len(questions)} questions au lieu de {count}. Merci de réessayer."
        )

    return questions


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate() -> str:
    theme = request.form.get("theme", "")
    num_questions = request.form.get("num_questions", "")
    difficulty = request.form.get("difficulty", "")

    try:
        clean_theme, count, level = validate_form_data(theme, num_questions, difficulty)
        questions = generate_quiz_with_groq(clean_theme, count, level)
    except QuizGenerationError as err:
        flash(str(err), "error")
        return redirect(url_for("index"))

    session["quiz_questions"] = questions
    session["quiz_meta"] = {
        "theme": clean_theme,
        "difficulty": level,
    }
    return render_template("quiz.html", questions=questions, meta=session["quiz_meta"])


@app.route("/result", methods=["POST"])
def result() -> str:
    questions = session.get("quiz_questions")
    meta = session.get("quiz_meta", {})

    if not questions:
        flash("Aucun quiz actif. Veuillez générer un quiz d'abord.", "error")
        return redirect(url_for("index"))

    results = []
    score = 0

    for idx, question in enumerate(questions):
        user_answer = request.form.get(f"q_{idx}")
        correct_answer = question["answer"]
        is_correct = user_answer == correct_answer
        if is_correct:
            score += 1

        results.append(
            {
                "question": question["question"],
                "options": question["options"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
            }
        )

    return render_template(
        "result.html",
        score=score,
        total=len(questions),
        results=results,
        meta=meta,
    )


if __name__ == "__main__":
    app.run(debug=True)
