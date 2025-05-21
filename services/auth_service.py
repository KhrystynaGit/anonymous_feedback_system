from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from services.db_service import verify_admin_user

security = HTTPBasic()

def verify_credentials(creds: HTTPBasicCredentials = Depends(security)):
    if not verify_admin_user(creds.username, creds.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username
