from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services.auth_service import verify_credentials
from services.db_service import (
    add_institution, get_all_institutions, load_all_feedback_for_institution,
    verify_admin_user, update_admin_password
)

router = APIRouter()
templates = Jinja2Templates(directory="app_templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, user: str = Depends(verify_credentials)):
    institutions = get_all_institutions()
    feedbacks = []
    selected_institution = None
    # Спочатку інституція не вибрана, відгуки не завантажені
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "institutions": institutions,
        "feedbacks": feedbacks,
        "user": user,
        "selected_institution": selected_institution
    })


@router.get("/admin/feedbacks", response_class=HTMLResponse)
async def get_feedbacks(
    request: Request,
    code: str,
    spam: str = 'all',
    sentiment: str = 'all',
    length: str = 'all',
    order: str = 'desc',
    user: str = Depends(verify_credentials)
):
    feedbacks = load_all_feedback_for_institution(
        code,
        spam_filter=spam,
        sentiment_filter=sentiment,
        length_filter=length,
        order=order
    )
    return templates.TemplateResponse("partials/feedbacks_table.html", {
        "request": request,
        "feedbacks": feedbacks
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


@router.get("/admin/institutions_list", response_class=HTMLResponse)
async def institutions_list(user: str = Depends(verify_credentials)):
    institutions = get_all_institutions()
    return templates.TemplateResponse("partials/institutions_options.html", {
        "institutions": institutions
    })


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
        update_admin_password(user, new_password)
        success = "Пароль успішно змінено."

    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": user,
        "error": error,
        "success": success
    })
