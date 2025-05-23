import os, random, string
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# База даних
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///feedback.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Моделі
class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    official_name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True)
    institution_code = Column(String, index=True)
    subject = Column(String)
    text = Column(Text, nullable=False)
    secret_text = Column(Text)
    lang = Column(String)
    sentiment = Column(String)
    spam = Column(Boolean)
    tags = Column(String)
    secret_sentiment = Column(String)
    secret_spam = Column(Boolean)
    secret_spam_score = Column(Float)

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

class AdminSecrets(Base):
    __tablename__ = "admin_secrets"
    id = Column(Integer, primary_key=True)
    secret_view_password = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Функції доступу до БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_random_code(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def validate_institution_code(code: str) -> bool:
    return bool(code) and len(code) == 8 and all(c in string.ascii_lowercase + string.digits for c in code)

def add_institution(official_name):
    db = SessionLocal()
    try:
        while True:
            code = generate_random_code()
            exists = db.query(Institution).filter_by(code=code).first()
            if not exists:
                break
        new_inst = Institution(official_name=official_name, code=code)
        db.add(new_inst)
        db.commit()
        return code
    finally:
        db.close()

def get_all_institutions():
    db = SessionLocal()
    try:
        return db.query(Institution).order_by(Institution.id).all()
    finally:
        db.close()

def get_institution_by_code(code):
    db = SessionLocal()
    try:
        inst = db.query(Institution).filter_by(code=code).first()
        return (inst.official_name, inst.code) if inst else None
    finally:
        db.close()

def save_feedback_for_institution(
    institution_code,
    text,
    lang,
    sentiment,
    spam,
    tags=None,
    subject=None,
    secret_text=None,
    secret_sentiment=None,
    secret_spam=None,
    secret_spam_score=None
):
    db = SessionLocal()
    try:
        feedback = Feedback(
            institution_code=institution_code,
            subject=subject,
            text=text,
            secret_text=secret_text,
            lang=lang,
            sentiment=sentiment,
            spam=spam,
            tags=tags,
            secret_sentiment=secret_sentiment,
            secret_spam=secret_spam,
            secret_spam_score=secret_spam_score
        )
        db.add(feedback)
        db.commit()
    finally:
        db.close()

def load_all_feedback_for_institution(
    institution_code,
    spam_filter='all',
    sentiment_filter='all',
    length_filter='all',
    order='desc',
    tags_filter='all'
):
    db = SessionLocal()
    try:
        query = db.query(Feedback).filter(Feedback.institution_code == institution_code)

        # Фільтр спаму
        if spam_filter == 'spam':
            query = query.filter(Feedback.spam == True)
        elif spam_filter == 'ham':
            query = query.filter(Feedback.spam == False)

        # Фільтр сентименту (нечутливий до регістру)
        if sentiment_filter.lower() != 'all':
            query = query.filter(func.lower(Feedback.sentiment) == sentiment_filter.lower())

        # Фільтр довжини
        if length_filter == 'short':
            query = query.filter(Feedback.text.op('length')() <= 100)
        elif length_filter == 'long':
            query = query.filter(Feedback.text.op('length')() > 100)

        # Фільтр тегів
        if tags_filter != 'all':
            query = query.filter(Feedback.tags.like(f"%{tags_filter}%"))

        # Сортування
        if order == 'asc':
            query = query.order_by(Feedback.id.asc())
        else:
            query = query.order_by(Feedback.id.desc())

        results = query.all()
        return [
            (f.id, f.subject, f.text, f.secret_text, f.lang, f.sentiment, f.spam, f.tags, f.secret_sentiment, f.secret_spam, f.secret_spam_score)
            for f in results
        ]
    finally:
        db.close()

def get_feedback_secret_text_by_id_and_code(feedback_id: int, institution_code: str):
    db = SessionLocal()
    try:
        f = db.query(Feedback).filter_by(id=feedback_id, institution_code=institution_code).first()
        return f.secret_text if f else None
    finally:
        db.close()

def get_feedback_secret_meta_by_id_and_code(feedback_id: int, institution_code: str):
    db = SessionLocal()
    try:
        f = db.query(Feedback).filter_by(id=feedback_id, institution_code=institution_code).first()
        if f:
            return f.secret_sentiment, f.secret_spam, f.secret_spam_score
        return None, None, None
    finally:
        db.close()

def create_admin_table_if_not_exists():
    Base.metadata.create_all(bind=engine)

def add_admin_user(username, password):
    from services.auth_service import hash_password
    db = SessionLocal()
    try:
        if not db.query(Admin).filter_by(username=username).first():
            hashed = hash_password(password)
            db.add(Admin(username=username, password_hash=hashed.decode()))
            db.commit()
    finally:
        db.close()

def verify_admin_user(username, password):
    from services.auth_service import verify_password
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(username=username).first()
        return verify_password(password, admin.password_hash) if admin else False
    finally:
        db.close()

def update_admin_password(username, new_password_hash):
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(username=username).first()
        if admin:
            admin.password_hash = new_password_hash
            db.commit()
    finally:
        db.close()

def set_secret_view_password(password: str):
    db = SessionLocal()
    try:
        db.query(AdminSecrets).delete()
        db.add(AdminSecrets(id=1, secret_view_password=password))
        db.commit()
    finally:
        db.close()

def get_secret_view_password() -> str:
    db = SessionLocal()
    try:
        s = db.query(AdminSecrets).filter_by(id=1).first()
        return s.secret_view_password if s else ""
    finally:
        db.close()

def generate_random_password(length=24):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
