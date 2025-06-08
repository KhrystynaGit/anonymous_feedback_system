from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import os
from uuid import uuid4

from services.nlp_service import detect_language, analyze_sentiment
from services.spam_service import detect_spam
from services.db_service import (
    save_feedback_for_institution,
    save_attachments,
    get_institution_by_code,
)

router = APIRouter()
templates = Jinja2Templates(directory="app_templates")
UPLOAD_DIR = "uploads"

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
    tags: Optional[str] = Form(""),
    files: List[UploadFile] = File([])
):
    institution_code = institution_code.strip()
    subject = subject.strip()
    text = text.strip()
    secret_text = (secret_text or "").strip()
    tags = tags.strip()

    attachment_files = [f for f in files if f.filename]
    if len(attachment_files) > 5:
        return templates.TemplateResponse(
            "feedback_form.html",
            {
                "request": request,
                "institution_code": institution_code,
                "error": "Максимум 5 файлів."
            },
        )

    if len(subject) < 3:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Тема відгуку занадто коротка."
        })
    if len(subject) > 255:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Тема відгуку занадто довга (макс. 255 символів)."
        })
    if len(text) < 3:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Зміст відгуку занадто короткий."
        })
    if len(text) > 5000:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Зміст відгуку занадто довгий (макс. 5000 символів)."
        })
    if secret_text and len(secret_text) > 5000:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Секретний зміст занадто довгий (макс. 5000 символів)."
        })
    if tags and len(tags) > 255:
        return templates.TemplateResponse("feedback_form.html", {
            "request": request,
            "institution_code": institution_code,
            "error": "Занадто багато тегів або занадто довгий рядок тегів (макс. 255 символів)."
        })

    lang = detect_language(text)
    sentiment = analyze_sentiment(text)
    spam, score = detect_spam(text)

    sentiment_secret = analyze_sentiment(secret_text) if secret_text else None
    spam_secret, score_secret = detect_spam(secret_text) if secret_text else (0, 0.0)

    feedback_id = save_feedback_for_institution(
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

    if attachment_files:
        dest_dir = os.path.join(UPLOAD_DIR, str(feedback_id))
        os.makedirs(dest_dir, exist_ok=True)
        attachments = []
        for upload in attachment_files:
            unique_name = f"{uuid4().hex}_{upload.filename}"
            file_path = os.path.join(dest_dir, unique_name)
            with open(file_path, "wb") as f:
                content = await upload.read()
                f.write(content)
            attachments.append((upload.filename, file_path))
        if attachments:
            save_attachments(feedback_id, attachments)

    return templates.TemplateResponse("success.html", {
        "request": request,
        "lang": lang,
        "sentiment": sentiment,
        "spam": spam,
        "score": f"{score:.3f}"
    })
