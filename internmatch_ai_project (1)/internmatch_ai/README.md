# InternMatch AI — NLP-Based Internship Recommendation Website

A Flask web app with account registration/login, editable student profiles, resume upload, TF-IDF/cosine-similarity recommendations, skill-gap insights, and saved internships.

## Stack
- Python + Flask
- SQLite
- scikit-learn (TF-IDF + cosine similarity)
- PyMuPDF for PDF resumes
- python-docx for DOCX resumes
- HTML, CSS, Jinja templates

## Requirements
Python 3.10+ recommended.

## Run locally

### Windows (PowerShell)
```powershell
cd internmatch_ai
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "replace-this-with-a-long-random-secret"
python app.py
```

### macOS / Linux
```bash
cd internmatch_ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="replace-this-with-a-long-random-secret"
python app.py
```

Open http://127.0.0.1:5000

## How to test
1. Create an account with an email and password (8+ characters).
2. Complete your profile and add skills/interests.
3. Optionally upload a PDF, DOCX or TXT resume (max 5 MB).
4. Save the profile. The dashboard ranks sample internships.
5. Bookmark an internship; view it under Saved.

## Recommendation logic
The engine builds TF-IDF vectors for the combined student profile and internship descriptions, then uses cosine similarity. It blends text similarity (70%) with detected skill overlap (30%). Location and work-mode preferences adjust the score. The displayed score is a heuristic relevance score, not a hiring probability.

## Important demo limitations
- Internship listings and `example.com` apply URLs are sample data, not real verified vacancies.
- Replace the `SEED_INTERNSHIPS` list in `app.py` with validated, current listings before real-world deployment.
- Resume text is stored in SQLite and uploads are stored under `uploads/`; this is a learning demo. Add a privacy policy, file-retention/deletion controls, CSRF protection, rate limiting, secure production secret management, HTTPS, and production server configuration before deployment.
- `debug=True` is for local development only. Do not use it in production.
- Email verification, password reset, OAuth, and administrator job-management are not implemented in this starter.
- Uploaded documents can contain sensitive information. Only upload resumes you have permission to process.

## Project structure
```text
internmatch_ai/
├── app.py
├── recommender.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── auth.html
│   ├── profile.html
│   ├── dashboard.html
│   └── saved.html
├── static/
│   └── style.css
└── uploads/              # created automatically
```


## Deploy on Render (portfolio demo)

1. Push this project folder to a GitHub repository. Do not upload `.venv`, `internmatch.db`, or personal resumes.
2. In Render, create **New > Web Service** and connect the repository.
3. Use these settings:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Add environment variable `SECRET_KEY` with a long random value.
4. Deploy and test the generated `onrender.com` URL.

Important: Render's free web-service filesystem is ephemeral. This app's SQLite database and resume files can be lost on restart/redeploy. Treat this as a portfolio demo only unless the database and uploaded files are moved to persistent services. Do not upload real/sensitive resumes to a public demo.
