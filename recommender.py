import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_TERMS = [
    "python", "java", "kotlin", "c++", "sql", "html", "css", "javascript", "react",
    "flask", "rest api", "git", "machine learning", "deep learning", "nlp", "tf-idf",
    "scikit-learn", "pandas", "numpy", "statistics", "data visualization", "excel",
    "opencv", "pytorch", "tensorflow", "android", "jetpack compose", "networking",
    "linux", "cybersecurity", "security testing", "research", "communication"
]

def clean_text(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def find_skills(text):
    normalized = clean_text(text)
    found = []
    for skill in SKILL_TERMS:
        if re.search(r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])", normalized):
            found.append(skill)
    return sorted(set(found))

def recommend_internships(profile_text, preferred_location, work_mode, internships):
    rows = list(internships)
    if not rows:
        return []
    profile_text = clean_text(profile_text)
    documents = []
    for item in rows:
        documents.append(clean_text(" ".join([
            item["title"], item["description"], item["skills"], item["eligibility"]
        ])))
    # TF-IDF learns terms from the profile and all available internship descriptions.
    corpus = [profile_text or "student looking for an internship"] + documents
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
    matrix = vectorizer.fit_transform(corpus)
    similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()

    student_skills = set(find_skills(profile_text))
    output = []
    for item, similarity in zip(rows, similarities):
        required = set(find_skills(item["skills"] + " " + item["description"]))
        matched = sorted(student_skills & required)
        missing = sorted(required - student_skills)
        # Transparent blend: semantic-ish TF-IDF text relevance plus skill overlap.
        skill_score = len(matched) / max(1, len(required))
        score = (0.70 * float(similarity) + 0.30 * skill_score) * 100
        location = (preferred_location or "Any").strip().lower()
        mode = (work_mode or "Any").strip().lower()
        if location not in ("", "any") and location not in item["location"].lower() and item["location"].lower() != "remote":
            score *= 0.72
        if mode not in ("", "any") and mode != item["mode"].lower():
            score *= 0.82
        output.append({
            "id": item["id"], "title": item["title"], "company": item["company"],
            "description": item["description"], "skills": item["skills"],
            "location": item["location"], "mode": item["mode"], "duration": item["duration"],
            "stipend": item["stipend"], "eligibility": item["eligibility"], "apply_url": item["apply_url"],
            "score": round(min(99, max(0, score))), "matched": matched, "missing": missing
        })
    output.sort(key=lambda x: x["score"], reverse=True)
    return output

def extract_resume_text(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        import fitz
        chunks = []
        with fitz.open(path) as pdf:
            for page in pdf:
                chunks.append(page.get_text())
        return "\n".join(chunks)
    if suffix == ".docx":
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Unsupported resume file")
