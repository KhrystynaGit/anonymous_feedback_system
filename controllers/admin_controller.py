from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services.auth_service import verify_credentials, hash_password
from services.db_service import (
    add_institution, get_all_institutions, load_all_feedback_for_institution,
    verify_admin_user, update_admin_password,
    get_feedback_secret_text_by_id_and_code,
    get_feedback_secret_meta_by_id_and_code,
    get_secret_view_password,
    validate_institution_code,
    get_attachments_for_feedback,
)

router = APIRouter()
templates = Jinja2Templates(directory="app_templates")

class SecretTextRequest(BaseModel):
    id: int
    code: str
    password: str

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, user: str = Depends(verify_credentials)):
    institutions = get_all_institutions()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "institutions": institutions,
        "feedbacks": [],
        "user": user,
        "selected_institution": None
    })

@router.get("/admin/feedbacks", response_class=HTMLResponse)
async def get_feedbacks(
    request: Request,
    code: str = None,
    spam: str = 'all',
    sentiment: str = 'all',
    length: str = 'all',
    order: str = 'desc',
    user: str = Depends(verify_credentials)
):
    tags = request.query_params.get('tags', 'all')
    if not code or not validate_institution_code(code):
        return templates.TemplateResponse("partials/feedbacks_table.html", {
            "request": request,
            "feedbacks": [],
            "selected_institution": code or ""
        })

    feedbacks = load_all_feedback_for_institution(
        code,
        spam_filter=spam,
        sentiment_filter=sentiment,
        length_filter=length,
        order=order,
        tags_filter=tags
    )
    return templates.TemplateResponse("partials/feedbacks_table.html", {
        "request": request,
        "feedbacks": feedbacks,
        "selected_institution": code
    })

@router.get("/admin/add_institution", response_class=HTMLResponse)
async def add_institution_form(request: Request, user: str = Depends(verify_credentials)):
    return templates.TemplateResponse("partials/add_institution_form.html", {
        "request": request,
        "user": user
    })

@router.post("/admin/add_institution", response_class=HTMLResponse)
async def add_new_institution(
    request: Request,
    official_name: str = Form(...),
    user: str = Depends(verify_credentials)
):
    code = add_institution(official_name)
    message = f"Інституцію '{official_name}' успішно додано з кодом: {code}"
    headers = {"HX-Trigger": "institutionAdded"}
    return templates.TemplateResponse("partials/add_institution_form.html", {
        "request": request,
        "message": message
    }, headers=headers)

@router.get("/admin/institutions_options", response_class=HTMLResponse)
async def institutions_options(
    current: str | None = None,
    user: str = Depends(verify_credentials)
):
    institutions = get_all_institutions()
    options = [
        f'<option value="" disabled{" selected" if not current else ""}>'
        'Оберіть інституцію</option>'
    ]
    for inst in institutions:
        sel = ' selected' if current == inst.code else ''
        options.append(f'<option value="{inst.code}"{sel}>{inst.official_name}</option>')
    return HTMLResponse(content="".join(options))

@router.get("/admin/change_password", response_class=HTMLResponse)
async def change_password_form(request: Request, user: str = Depends(verify_credentials)):
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": user,
        "error": None,
        "success": None
    })

@router.post("/admin/change_password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: str = Depends(verify_credentials),
):
    error = None
    success = None

    if new_password != confirm_password:
        error = "Новий пароль і підтвердження не співпадають."
    elif not verify_admin_user(user, old_password):
        error = "Старий пароль неправильний."
    else:
        hashed_password = hash_password(new_password).decode()
        update_admin_password(user, hashed_password)
        success = "Пароль успішно змінено."

    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": user,
        "error": error,
        "success": success
    })

@router.post("/admin/get_secret_text")
async def get_secret_text(
    request_data: SecretTextRequest,
    user: str = Depends(verify_credentials)
):
    real_password = get_secret_view_password()
    if request_data.password != real_password:
        return JSONResponse({"success": False, "error": "Неправильний пароль."})

    secret_text = get_feedback_secret_text_by_id_and_code(request_data.id, request_data.code)
    sentiment, spam, _score = get_feedback_secret_meta_by_id_and_code(request_data.id, request_data.code)

    if secret_text is None:
        return JSONResponse({"success": False, "error": "Секретний текст не знайдено."})

    return JSONResponse({
        "success": True,
        "secret_text": secret_text,
        "secret_sentiment": sentiment,
        "secret_spam": spam
    })


@router.get("/admin/attachments/{feedback_id}", response_class=HTMLResponse)
async def attachments_view(request: Request, feedback_id: int, user: str = Depends(verify_credentials)):
    files = get_attachments_for_feedback(feedback_id)
    return templates.TemplateResponse(
        "attachments_list.html",
        {"request": request, "attachments": files, "feedback_id": feedback_id}
    )
