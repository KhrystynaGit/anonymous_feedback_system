@echo off
SETLOCAL

REM Check if the virtual environment exists
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install all dependencies only once from requirements.txt
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Start FastAPI server
echo Starting FastAPI server...
python -m uvicorn app_main:app --host 0.0.0.0 --port 8000 --reload

pause
ENDLOCAL
