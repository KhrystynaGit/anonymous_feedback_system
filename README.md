# Anonymous Feedback System

Simple web app for anonymous collection of feedback with spam detection and sentiment analysis.

---

## Features

- Submit anonymous feedback by institution code  
- Spam detection with a fine-tuned transformer model  
- Sentiment analysis (multilingual)  
- Admin panel to manage institutions and view feedback  
- QR code scanning support for easy institution code input  

---

## Requirements

- Python 3.10+  
- [pip](https://pip.pypa.io/en/stable/)  

---

## Setup & Run
(for windows just run start.bat)

1. Clone the repo  
2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate.bat # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:

   ```bash
   uvicorn app_main:app --reload
   ```

5. Open http://127.0.0.1:8000 in your browser  

6. Admin panel available at http://127.0.0.1:8000/admin  
   - Default admin username: `admin`  
   - Password is auto-generated on first run and saved in `deleteme.txt` file  

---

## Notes

- Database: SQLite (`feedback.db` in project root)  
- Passwords hashed with bcrypt  
- Spam model is loaded from local folder `spam_model_dofinetuned2`  (there is no model, so you need to use yours, i used xlm-roberta as base)
- Change admin password immediately after first login  
