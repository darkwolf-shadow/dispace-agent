import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytesseract
import requests
from duckduckgo_search import DDGS
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from PIL import Image
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, Integer, String, Text, TypeDecorator, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


class JSONString(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/dispace"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    tavily_api_key: Optional[str] = None
    clearbit_api_key: Optional[str] = None
    uploads_dir: str = "/app/uploads"

    class Config:
        env_file = ".env"


settings = Settings()
os.makedirs(settings.uploads_dir, exist_ok=True)

openai_client = None
if settings.openrouter_api_key:
    openai_client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)
elif settings.openai_api_key:
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    openai_client = OpenAI(**kwargs)

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
    raw_text = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    tags = Column(JSONString, nullable=True)
    score = Column(Integer, default=0)
    report = Column(Text, nullable=True)
    source_links = Column(JSONString, nullable=True)
    social_links = Column(JSONString, nullable=True)
    enriched_at = Column(DateTime, nullable=True)
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


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    report: Optional[str] = None
    source_links: Optional[Dict[str, Any]] = None
    social_links: Optional[Dict[str, Any]] = None


class ContactOut(ContactUpdate):
    id: int
    raw_text: Optional[str] = None
    image_path: Optional[str] = None
    enriched_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    contact_id: int
    report: Optional[str] = None


app = FastAPI(title="DiSpace Lead Capture API", version="0.2.0")
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
        if not data["email"]:
            m = re.search(r"[\w.-]+@[\w.-]+\.\w{2,}", line)
            if m:
                data["email"] = m.group(0)
                continue

        if not data["phone"] and re.search(r"[\+]?[(]?[0-9]{2,}[)]?[-\s\./0-9]{6,}", line):
            data["phone"] = normalize_phone(line)
            continue

        if not data["website"]:
            m = re.search(r"(https?://)?(www\.)?([\w-]+\.[\w.-]+)", line, re.IGNORECASE)
            if m and not m.group(0).lower().endswith((".jpg", ".png")):
                data["website"] = m.group(0)
                continue

        if "linkedin.com" in line.lower():
            data["linkedin"] = line.split()[-1]
            continue

    if lines:
        data["name"] = lines[0]
    if len(lines) > 1:
        data["role"] = lines[1]
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


# -------------------- Enrichment & Report Services --------------------


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    if settings.tavily_api_key:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                },
                timeout=20,
            )
            resp.raise_for_status()
            return [
                {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")}
                for r in resp.json().get("results", [])
            ]
        except Exception as exc:
            print("Tavily error:", exc)

    try:
        with DDGS() as ddgs:
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                for r in ddgs.text(query, max_results=max_results)
            ]
    except Exception as exc:
        print("DDGS error:", exc)

    return []


def detect_social_links(text: str, results: List[Dict[str, str]]) -> Dict[str, str]:
    links = {}
    pattern_map = {
        "linkedin": r"https?://(www\.)?linkedin\.com/[\w/-]+",
        "twitter": r"https?://(www\.)?(twitter|x)\.com/[\w/-]+",
        "facebook": r"https?://(www\.)?facebook\.com/[\w/-]+",
        "instagram": r"https?://(www\.)?instagram\.com/[\w/-]+",
    }
    combined = text + "\n" + "\n".join(r.get("snippet", "") + " " + r.get("url", "") for r in results)
    for platform, pattern in pattern_map.items():
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            links[platform] = m.group(0)
    return links


def enrich_contact_data(contact: Contact) -> Dict[str, Any]:
    results = []
    if contact.company:
        results.extend(search_web(f"{contact.company} azienda sito ufficiale contatti", max_results=5))
    if contact.name and contact.company:
        results.extend(search_web(f"{contact.name} {contact.company} LinkedIn", max_results=5))
    elif contact.name:
        results.extend(search_web(f"{contact.name} LinkedIn", max_results=3))

    snippets = "\n".join(r.get("snippet", "") for r in results)
    links = detect_social_links(snippets, results)
    return {"results": results, "social_links": links}


def score_and_tag(contact: Contact) -> (int, List[str]):
    score = 0
    tags = []
    if contact.email:
        score += 20
        tags.append("has_email")
    if contact.phone:
        score += 15
        tags.append("has_phone")
    if contact.website:
        score += 10
        tags.append("has_website")
    if contact.linkedin:
        score += 15
        tags.append("has_linkedin")
    if contact.company:
        score += 15
        tags.append("has_company")
    if contact.role:
        score += 10
        tags.append("has_role")
    if contact.report:
        score += 15
        tags.append("enriched")
    return min(score, 100), tags


def generate_report(contact: Contact, enrichment: Dict[str, Any]) -> str:
    data = enrichment.get("results", [])
    social = enrichment.get("social_links", {})
    snippets = "\n".join(f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in data[:5])

    if openai_client:
        try:
            prompt = (
                "Genera un report sintetico in italiano per il seguente contatto, "
                "basandoti sui riferimenti web trovati. Massimo 300 parole.\n\n"
                f"Nome: {contact.name}\nAzienda: {contact.company}\nRuolo: {contact.role}\n"
                f"Sito: {contact.website}\nLinkedIn: {contact.linkedin}\n\n"
                f"Riferimenti:\n{snippets}\n"
            )
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sei un assistente di vendita B2B."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=600,
            )
            return resp.choices[0].message.content
        except Exception as exc:
            print("OpenAI report error:", exc)

    lines = [
        f"Report contatto: {contact.name or 'N/D'}",
        f"Azienda: {contact.company or 'N/D'}",
        f"Ruolo: {contact.role or 'N/D'}",
        f"Email: {contact.email or 'N/D'}",
        f"Telefono: {contact.phone or 'N/D'}",
        f"Sito web: {contact.website or 'N/D'}",
        f"LinkedIn: {contact.linkedin or 'N/D'}",
        "",
        "Riferimenti web trovati:",
    ]
    for r in data[:5]:
        lines.append(f"- {r.get('title', '')}: {r.get('url', '')}")
    if social:
        lines.append("")
        lines.append("Social rilevati:")
        for k, v in social.items():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


# -------------------- API Endpoints --------------------


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


@app.post("/contacts/{contact_id}/enrich", response_model=ContactOut)
def enrich_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    enrichment = enrich_contact_data(contact)
    contact.source_links = enrichment.get("results", [])
    contact.social_links = enrichment.get("social_links", {})
    contact.report = generate_report(contact, enrichment)
    contact.score, contact.tags = score_and_tag(contact)
    contact.enriched_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)
    return contact


@app.get("/contacts/{contact_id}/report", response_model=ReportOut)
def get_report(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if not contact.report:
        raise HTTPException(status_code=400, detail="Contact not enriched yet")
    return {"contact_id": contact.id, "report": contact.report}


@app.get("/segments")
def list_segments(db: Session = Depends(get_db)):
    """Restituisce segmenti automatici basati su tag e score."""
    contacts = db.query(Contact).all()
    segments = {
        "hot_leads": [c.id for c in contacts if c.score and c.score >= 70],
        "with_email": [c.id for c in contacts if c.email],
        "with_company": [c.id for c in contacts if c.company],
        "enriched": [c.id for c in contacts if c.enriched_at],
        "tag_counts": {},
    }
    for c in contacts:
        if c.tags:
            for tag in c.tags:
                segments["tag_counts"][tag] = segments["tag_counts"].get(tag, 0) + 1
    return segments


@app.get("/health")
def health():
    return {"status": "ok"}


if os.path.exists("/app/frontend"):
    app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
