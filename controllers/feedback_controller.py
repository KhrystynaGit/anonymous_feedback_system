from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services.nlp_service import detect_language, analyze_sentiment
from services.spam_service import detect_spam
from services.db_service import save_feedback_for_institution, create_feedback_table_for_institution, get_institution_by_code

router = APIRouter()
templates = Jinja2Templates(directory="app_templates")

@router.get("/", response_class=HTMLResponse)
async def code_or_form(request: Request):
    return templates.TemplateResponse("code_or_form.html", {"request": request, "show_form": False})

@router.post("/enter_code", response_class=HTMLResponse)
async def check_institution_code(request: Request, code: str = Form(...)):
    code = code.strip()
    institution = get_institution_by_code(code)
    if not institution:
        return templates.TemplateResponse("code_or_form.html", {
            "request": request,
            "show_form": False,
            "error": "Некоректний код інституції."
        })
    official_name = institution[0]
    return templates.TemplateResponse("code_or_form.html", {
        "request": request,
        "show_form": True,
        "institution_code": code,
        "official_name": official_name
    })

@router.post("/submit", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    text: str = Form(...),
    institution_code: str = Form(...)
):
    text = text.strip()
    institution_code = institution_code.strip()

    if len(text) < 3 or not institution_code:
        return templates.TemplateResponse("code_or_form.html", {
            "request": request,
            "show_form": True,
            "error": "Текст або код інституції не можуть бути порожніми.",
            "institution_code": institution_code
        })

    lang = detect_language(text)
    sentiment = analyze_sentiment(text)
    spam, score = detect_spam(text)

    create_feedback_table_for_institution(institution_code)
    save_feedback_for_institution(institution_code, text, lang, sentiment, spam)

    return templates.TemplateResponse("success.html", {
        "request": request,
        "lang": lang,
        "sentiment": sentiment,
        "spam": spam,
        "score": f"{score:.3f}"
    })
