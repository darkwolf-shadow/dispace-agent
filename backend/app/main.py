import os
import re
import uuid
from datetime import datetime
from typing import List, Optional

import pytesseract
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/dispace"
    openai_api_key: Optional[str] = None
    uploads_dir: str = "/app/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
os.makedirs(settings.uploads_dir, exist_ok=True)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    role = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    raw_text = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class ContactCreate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None


class ContactOut(ContactCreate):
    id: int
    raw_text: Optional[str] = None
    image_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


app = FastAPI(title="DiSpace Lead Capture API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_phone(value: str) -> str:
    return re.sub(r"[^\d+\-()\s]", "", value).strip()


def extract_fields(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data = {
        "name": None,
        "company": None,
        "role": None,
        "email": None,
        "phone": None,
        "website": None,
        "address": None,
        "linkedin": None,
    }

    for line in lines:
        # Email
        if not data["email"]:
            m = re.search(r"[\w.-]+@[\w.-]+\.\w{2,}", line)
            if m:
                data["email"] = m.group(0)
                continue

        # Phone
        if not data["phone"] and re.search(r"[\+]?[(]?[0-9]{2,}[)]?[-\s\./0-9]{6,}", line):
            data["phone"] = normalize_phone(line)
            continue

        # Website
        if not data["website"]:
            m = re.search(r"(https?://)?(www\.)?([\w-]+\.[\w.-]+)", line, re.IGNORECASE)
            if m and not m.group(0).lower().endswith((".jpg", ".png")):
                data["website"] = m.group(0)
                continue

        # LinkedIn
        if "linkedin.com" in line.lower():
            data["linkedin"] = line.split()[-1]
            continue

    # Heuristics for name / role / company
    if lines:
        data["name"] = lines[0]
    if len(lines) > 1:
        data["role"] = lines[1]
    # Company often has S.r.l., S.p.A., srl, spa, Ltd, etc.
    for line in lines:
        if re.search(r"\b(S\.r\.l|Srl|S\.p\.A|Spa|Ltd|LLC|GmbH|Inc\.?)\b", line, re.IGNORECASE):
            data["company"] = line
            break
    if not data["company"] and len(lines) > 2:
        data["company"] = lines[2]

    return data


def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or ".jpg")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.uploads_dir, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def run_ocr(image_path: str) -> str:
    image = Image.open(image_path)
    return pytesseract.image_to_string(image, lang="ita+eng")


@app.post("/upload", response_model=ContactOut)
def upload_business_card(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_path = save_upload(file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    try:
        raw_text = run_ocr(image_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

    fields = extract_fields(raw_text)
    contact = Contact(raw_text=raw_text, image_path=image_path, **fields)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@app.post("/contacts", response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    contact = Contact(**payload.model_dump(exclude_unset=True))
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@app.get("/contacts", response_model=List[ContactOut])
def list_contacts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()


@app.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.get("/health")
def health():
    return {"status": "ok"}


if os.path.exists("/app/frontend"):
    app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
