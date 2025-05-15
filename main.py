from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import sqlite3
import os
import re
import string
import secrets
from langdetect import detect
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# --- NLP Models ---
model_name = "tabularisai/multilingual-sentiment-analysis"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# --- DB Setup ---
DB_PATH = "feedback.db"
if not os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE feedback
                 (
                     id        INTEGER PRIMARY KEY AUTOINCREMENT,
                     text      TEXT,
                     lang      TEXT,
                     sentiment TEXT,
                     spam      INTEGER
                 )''')
    conn.commit()
    conn.close()

# --- App Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

# --- Admin Credentials ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"


# --- Load Spam Keywords ---
def load_spam_keywords(filepath: str) -> list[str]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            keywords = [line.strip().lower() for line in f if line.strip()]
        return keywords
    except FileNotFoundError:
        print(f"⚠️ WARNING: Spam keyword file not found at {filepath}")
        return []


SPAM_KEYWORDS = load_spam_keywords("spam_keywords.txt")


# --- Helper Functions ---

# Функція для перевірки сміттєвих текстів
def is_garbage(text: str) -> bool:
    # Видалення зайвих пробілів
    text = text.strip()

    # Перевірка на занадто короткий текст (менше 5 символів)
    if len(text) < 5:
        return True

    # Перевірка на текст, який складається лише з цифр
    if text.isdigit():
        return True

    # Перевірка на текст, що складається з непотрібних символів (наприклад, лише розділові знаки)
    if re.match(r"^[\W_]+$", text):  # Тільки символи, цифри чи пробіли
        return True

    # Перевірка на наявність достатньої кількості осмислених слів
    words = re.findall(r'\b[a-zA-Zа-яА-Я]+\b', text)
    if len(words) < 3:  # Якщо є менше трьох осмислених слів
        return True

    # Перевірка на великий набір однакових символів (наприклад, багато кавичок або цифр)
    if len(set(text)) < 3:  # Якщо тільки кілька різних символів
        return True

    # Перевірка на випадкові символи або цифри
    # Якщо більше ніж 70% символів це не букви, не цифри, і не пробіли
    non_alphanumeric = len(re.findall(r"[^a-zA-Zа-яА-Я0-9]", text))
    if non_alphanumeric / len(text) > 0.7:  # більше 70% це не букви чи цифри
        return True

    return False

# Функція для детектування спаму
def detect_spam(text: str) -> int:
    text_lower = text.lower().strip()

    # Перевірка на наявність спам-ключових слів
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return 1

    # Перевірка на наявність URL
    if len(re.findall(r'https?://', text_lower)) >= 2:
        return 1

    # Перевірка на дуже короткий текст або сміття
    if len(text_lower) < 5 or re.fullmatch(r"[^a-zA-Zа-яА-Я0-9]+", text_lower):
        return 1

    # Перевірка на сміття
    if is_garbage(text):
        return 1

    return 0


# Аналіз настроїв
def analyze_sentiment(text: str) -> str:
    try:
        result = sentiment_pipeline(text[:512])
        return result[0]['label']
    except Exception:
        return "neutral"


# Перевірка облікових даних адміністратора
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/submit")
async def submit_feedback(request: Request, text: str = Form(...)):
    # Очищаємо текст від зайвих пробілів
    text = text.strip()

    # Перевірка на порожній або майже порожній текст
    if len(text) < 3:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Текст занадто короткий або порожній."
        })

    try:
        # Детектуємо мову
        lang = detect(text)
    except Exception:
        lang = "unknown"

    sentiment = analyze_sentiment(text)
    spam = detect_spam(text)

    # Збереження в базу даних
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (text, lang, sentiment, spam) VALUES (?, ?, ?, ?)",
              (text, lang, sentiment, spam))
    conn.commit()
    conn.close()

    return templates.TemplateResponse("success.html", {
        "request": request,
        "lang": lang,
        "sentiment": sentiment,
        "spam": spam
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, username: str = Depends(verify_credentials)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, text, lang, sentiment, spam FROM feedback ORDER BY id DESC")
    feedbacks = c.fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "feedbacks": feedbacks,
        "user": username
    })


# --- Entry Point ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
