from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from controllers.feedback_controller import router as feedback_router
from controllers.admin_controller import router as admin_router

from services.db_service import add_admin_user, verify_admin_user, set_secret_view_password, generate_random_password

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app_templates")

app.include_router(feedback_router)
app.include_router(admin_router)

ADMIN_USERNAME = "admin"
PASSWORD_FILE = "deleteme.txt"

def initialize_admin():
    if os.path.exists(PASSWORD_FILE):
        return

    if verify_admin_user(ADMIN_USERNAME, "any_password_that_wont_match"):
        return

    random_password = generate_random_password(24)
    secret_view_password = generate_random_password(12)

    add_admin_user(ADMIN_USERNAME, random_password)
    set_secret_view_password(secret_view_password)

    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write(f"Admin username: {ADMIN_USERNAME}\n")
        f.write(f"Admin password: {random_password}\n")
        f.write(f"Secret view password: {secret_view_password}\n")
        f.write("Please delete this file after first login and/or change password in web interface!\n")

initialize_admin()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_main:app", host="127.0.0.1", port=8000, reload=True)