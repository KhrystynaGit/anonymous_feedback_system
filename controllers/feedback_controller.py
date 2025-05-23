from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from services.nlp_service import detect_language, analyze_sentiment
from services.spam_service import detect_spam
from services.db_service import (
    save_feedback_for_institution,
    get_institution_by_code,
)

router = APIRouter()
templates = Jinja2Templates(directory="app_templates")

@router.get("/", response_class=HTMLResponse)
async def code_or_form(request: Request):
    return templates.TemplateResponse("code_input.html", {"request": request, "error": None})

@router.post("/enter_code", response_class=HTMLResponse)
async def check_institution_code(request: Request, code: str = Form(...)):
    code = code.strip()
    institution = get_institution_by_code(code)
    if not institution:
        return templates.TemplateResponse("code_input.html", {
            "request": request,
            "error": "Некоректний код інституції."
        })
    official_name = institution[0]
    return templates.TemplateResponse("feedback_form.html", {
        "request": request,
        "institution_code": code,
        "official_name": official_name,
        "error": None
    })

@router.post("/submit", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    institution_code: str = Form(...),
    subject: str = Form(...),
    text: str = Form(...),
    secret_text: Optional[str] = Form(None),
    tags: Optional[str] = Form("")
):
    institution_code = institution_code.strip()
    subject = subject.strip()
    text = text.strip()
    secret_text = (secret_text or "").strip()
    tags = tags.strip()

    if len(subject) < 3:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Тема відгуку занадто коротка."
        })
    if len(text) < 3:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Зміст відгуку занадто короткий."
        })

    lang = detect_language(text)
    sentiment = analyze_sentiment(text)
    spam, score = detect_spam(text)

    sentiment_secret = analyze_sentiment(secret_text) if secret_text else None
    spam_secret, score_secret = detect_spam(secret_text) if secret_text else (0, 0.0)

    save_feedback_for_institution(
        institution_code,
        text,
        lang,
        sentiment,
        spam,
        tags=tags,
        subject=subject,
        secret_text=secret_text,
        secret_sentiment=sentiment_secret,
        secret_spam=spam_secret,
        secret_spam_score=score_secret
    )

    return templates.TemplateResponse("success.html", {
        "request": request,
        "lang": lang,
        "sentiment": sentiment,
        "spam": spam,
        "score": f"{score:.3f}"
    })
