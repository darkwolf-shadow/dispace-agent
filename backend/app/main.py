import base64
import io
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytesseract
import requests
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, Integer, String, Text, TypeDecorator, create_engine, text
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
    database_url: str = "sqlite:////app/data/dispace.db"
    app_username: Optional[str] = None
    app_password: Optional[str] = None
    disable_auth: bool = False
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "https://localhost"
    openrouter_title: str = "DiSpace Lead Capture"
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    bing_api_key: Optional[str] = None
    clearbit_api_key: Optional[str] = None
    uploads_dir: str = "/app/data/uploads"
    app_title: str = "DiSpace Lead Capture"
    owner_name: str = ""
    plan: str = "pro"  # base, pro, premium

    class Config:
        env_file = ".env"


settings = Settings()
os.makedirs(settings.uploads_dir, exist_ok=True)

openai_client = None
if settings.openrouter_api_key:
    openai_client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        default_headers={
            "HTTP-Referer": settings.openrouter_http_referer,
            "X-Title": settings.openrouter_title,
        },
    )
elif settings.openai_api_key:
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    openai_client = OpenAI(**kwargs)

engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(settings.database_url, **engine_kwargs)
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
    extra = Column(JSONString, nullable=True)
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


class ContactNote(Base):
    __tablename__ = "contact_notes"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, nullable=False, index=True)
    note_type = Column(String, nullable=False, default="note")  # note, call, meeting, document
    content = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    products = Column(Text, nullable=True)
    services = Column(Text, nullable=True)
    values = Column("company_values", Text, nullable=True)
    target = Column(Text, nullable=True)
    channels = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    tone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # proposal, email, whatsapp, social, story
    channel = Column(String, nullable=True)  # email, whatsapp, instagram, linkedin
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    is_default = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    template_id = Column(Integer, nullable=True)
    filters = Column(JSONString, nullable=True)
    status = Column(String, default="draft")  # draft, ready, sent
    generated_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, nullable=False, index=True)
    campaign_id = Column(Integer, nullable=True, index=True)
    kind = Column(String, nullable=False)
    channel = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String, default="draft")  # draft, sent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    media_path = Column(String, nullable=True)  # photo or video
    media_type = Column(String, default="image")  # image, video
    platform = Column(String, nullable=False, default="instagram")  # instagram, facebook, whatsapp, linkedin, telegram
    caption = Column(Text, nullable=True)
    hashtags = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, approved, scheduled, published
    scheduled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialCredential(Base):
    __tablename__ = "social_credentials"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # facebook, instagram, whatsapp, telegram, linkedin
    label = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)
    extra = Column(JSONString, nullable=True)  # page_id, chat_id, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialPublishLog(Base):
    __tablename__ = "social_publish_logs"

    id = Column(Integer, primary_key=True, index=True)
    social_post_id = Column(Integer, nullable=False, index=True)
    platform = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, error
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# SQLite migration: add extra column if missing
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE contacts ADD COLUMN extra TEXT"))
except Exception:
    pass

# Create company_profiles table if missing
try:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR,
                description TEXT,
                products TEXT,
                services TEXT,
                company_values TEXT,
                target TEXT,
                channels TEXT,
                website VARCHAR,
                email VARCHAR,
                phone VARCHAR,
                address VARCHAR,
                tone VARCHAR,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
except Exception:
    pass


def seed_default_templates():
    db = SessionLocal()
    try:
        if db.query(Template).first():
            return
        defaults = [
            Template(
                name="Proposta commerciale default",
                kind="proposal",
                channel="email",
                subject="Proposta per {company}",
                body=(
                    "Gentile {name},\n\n"
                    "abbiamo seguito con interesse l’attività di {company} e vorremmo proporre una collaborazione "
                    "che possa supportare il vostro ruolo di {role}.\n\n"
                    "Restiamo a disposizione per un breve call al numero {phone} o via email {email}.\n\n"
                    "Cordiali saluti."
                ),
                is_default=1,
            ),
            Template(
                name="Messaggio WhatsApp default",
                kind="whatsapp",
                channel="whatsapp",
                body="Ciao {name}, sono {role} presso {company}? Vorremmo proporti una collaborazione. Scrivimi pure.",
                is_default=1,
            ),
            Template(
                name="Post LinkedIn default",
                kind="social",
                channel="linkedin",
                body="Siamo felici di collaborare con aziende come {company}. Contattaci per scoprire come possiamo aiutare {role} come {name}.",
                is_default=1,
            ),
            Template(
                name="Story Instagram default",
                kind="story",
                channel="instagram",
                body="Scorpi come aiutiamo {company} a crescere! DM per info. #{company}",
                is_default=1,
            ),
        ]
        for tmpl in defaults:
            db.add(tmpl)
        db.commit()
    finally:
        db.close()


seed_default_templates()


class ContactCreate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    report: Optional[str] = None
    source_links: Optional[Any] = None
    social_links: Optional[Any] = None


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


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    products: Optional[str] = None
    services: Optional[str] = None
    values: Optional[str] = None
    target: Optional[str] = None
    channels: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tone: Optional[str] = None


class CompanyProfileOut(CompanyProfileUpdate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    name: str
    kind: str
    channel: Optional[str] = None
    subject: Optional[str] = None
    body: str
    is_default: bool = False


class TemplateUpdate(TemplateCreate):
    pass


class TemplateOut(TemplateCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    name: str
    channel: str
    template_id: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None


class CampaignOut(CampaignCreate):
    id: int
    status: str
    generated_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GeneratedContentOut(BaseModel):
    id: int
    contact_id: int
    campaign_id: Optional[int] = None
    kind: str
    channel: Optional[str] = None
    subject: Optional[str] = None
    body: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactNoteCreate(BaseModel):
    note_type: str = "note"
    content: Optional[str] = None


class ContactNoteOut(ContactNoteCreate):
    id: int
    contact_id: int
    file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SocialPostCreate(BaseModel):
    platform: str = "instagram"
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class SocialPostOut(BaseModel):
    id: int
    media_path: Optional[str] = None
    media_type: str = "image"
    platform: str = "instagram"
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    status: str = "draft"
    scheduled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SocialCredentialCreate(BaseModel):
    platform: str
    label: Optional[str] = None
    access_token: str
    extra: Optional[str] = None


class SocialCredentialOut(BaseModel):
    id: int
    platform: str
    label: Optional[str] = None
    extra: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator('extra', mode='before')
    @classmethod
    def dump_extra(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        return v


app = FastAPI(title="DiSpace Lead Capture API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = {"/", "/login", "/health", "/app.js", "/style.css", "/favicon.ico"}
    if request.url.path in public_paths or request.method == "OPTIONS" or settings.disable_auth:
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        user, passwd = decoded.split(":", 1)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    if user != settings.app_username or passwd != settings.app_password:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)


security_basic = HTTPBasic()


@app.get("/login")
def login(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not settings.app_username or not settings.app_password:
        raise HTTPException(status_code=403, detail="Login not configured")
    if credentials.username != settings.app_username or credentials.password != settings.app_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_phone(value: str) -> str:
    return re.sub(r"[^\d+\-()\s]", "", value).strip()


def extract_fields(text: str, image_path: Optional[str] = None) -> dict:
    if openai_client and image_path:
        try:
            return extract_fields_with_vision(image_path)
        except Exception as exc:
            print("Vision extraction error:", exc)

    if openai_client:
        try:
            return extract_fields_with_llm(text)
        except Exception:
            pass

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
        "extra": None,
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


def extract_fields_with_llm(text: str) -> dict:
    prompt = (
        "Estrai i dati da questo biglietto da visita o volantino. Restituisci SOLO un oggetto JSON "
        "con le chiavi: name, company, role, email, phone, website, address, linkedin, extra. "
        "Se ci sono piu numeri di telefono, mettili tutti nella chiave phone separati da ' / '. "
        "Se ci sono piu indirizzi, mettili tutti nella chiave address separati da ' / '. "
        "Se vedi un sito web scritto come www.nomesito.com, nomesito.it o simile, inseriscilo nella chiave website. "
        "Se manca https:// non aggiungerlo. "
        "La chiave extra deve contenere solo i dati rilevanti trovati "
        "(partita iva, codice fiscale, CAP, citta, provincia, fax, note, prodotti, servizi). "
        "Ometti le chiavi di extra per cui non hai trovato nulla. Non scrivere testo fuori dal JSON.\n\n"
        f"{text}"
    )
    resp = openai_client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sei un estrattore di dati da biglietti da visita. Restituisci solo JSON."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
    )
    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        if content.startswith("json"):
            content = content[4:].strip()
    parsed = json.loads(content)
    return _normalize_llm_output(parsed)


def _normalize_llm_output(parsed: dict) -> dict:
    allowed = {"name", "company", "role", "email", "phone", "website", "address", "linkedin", "extra"}
    result = {k: parsed.get(k) for k in allowed}

    def to_str(value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ("null", "none", ""):
                return None
            return value
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value if v is not None) or None
        if isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items() if v is not None) or None
        return str(value).strip() or None

    for key in ["name", "company", "role", "email", "phone", "website", "address", "linkedin"]:
        result[key] = to_str(result.get(key))

    raw_extra = result.get("extra")
    if isinstance(raw_extra, dict):
        clean_extra = {
            k: v for k, v in raw_extra.items()
            if v is not None and str(v).strip() and str(v).strip().lower() not in ("null", "none")
        }
        result["extra"] = clean_extra or None
    else:
        result["extra"] = None
    return result


def extract_fields_with_vision(image_path: str) -> dict:
    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        # Resize to avoid huge payloads while keeping readability
        img.thumbnail((1600, 1600))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    prompt = (
        "Estrai i dati da questa immagine di un biglietto da visita o volantino. "
        "Restituisci SOLO un oggetto JSON con le chiavi: "
        "name, company, role, email, phone, website, address, linkedin, extra. "
        "Se ci sono piu numeri di telefono o indirizzi, mettili tutti nello stesso campo separati da ' / '. "
        "La chiave extra contenga solo dati extra rilevanti (partita iva, codice fiscale, CAP, citta, provincia, fax, note, prodotti, servizi). "
        "Ometti le chiavi di extra senza valore. Non scrivere testo fuori dal JSON."
    )
    resp = openai_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Sei un estrattore di dati da biglietti da visita e volantini. Restituisci solo JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
        max_tokens=700,
    )
    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        if content.startswith("json"):
            content = content[4:].strip()
    parsed = json.loads(content)
    return _normalize_llm_output(parsed)


def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or ".jpg")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.uploads_dir, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def deskew(image: Image.Image) -> Image.Image:
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        if angle:
            image = image.rotate(angle, expand=True, fillcolor=(255, 255, 255))
    except Exception:
        pass
    return image


def run_ocr(image_path: str) -> str:
    image = Image.open(image_path)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Scale up to improve small text readability
    width, height = image.size
    target = 2000
    scale = max(1, target / max(width, height))
    if scale > 1:
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    image = deskew(image)
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = ImageEnhance.Sharpness(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    configs = ["--psm 6", "--psm 3", "--psm 4", "--psm 11", "--psm 1"]
    best = ""
    for config in configs:
        text = pytesseract.image_to_string(gray, lang="ita+eng", config=config)
        if len(text.strip()) > len(best.strip()):
            best = text
    return best


# -------------------- Enrichment & Report Services --------------------


def _search_tavily(query: str, max_results: int) -> List[Dict[str, str]]:
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "max_results": max_results}
    if settings.tavily_api_key:
        headers["Authorization"] = f"Bearer {settings.tavily_api_key}"
    else:
        headers["X-Tavily-Access-Mode"] = "keyless"
    resp = requests.post(
        "https://api.tavily.com/search",
        headers=headers,
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")}
        for r in resp.json().get("results", [])
    ]


def _search_brave(query: str, max_results: int) -> List[Dict[str, str]]:
    if not settings.brave_api_key:
        return []
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
        params={"q": query, "count": max_results},
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description", "")}
        for r in resp.json().get("web", {}).get("results", [])
    ]


def _search_serper(query: str, max_results: int) -> List[Dict[str, str]]:
    if not settings.serper_api_key:
        return []
    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title"), "url": r.get("link"), "snippet": r.get("snippet", "")}
        for r in resp.json().get("organic", [])
    ]


def _search_bing(query: str, max_results: int) -> List[Dict[str, str]]:
    if not settings.bing_api_key:
        return []
    resp = requests.get(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": settings.bing_api_key},
        params={"q": query, "count": max_results},
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("name"), "url": r.get("url"), "snippet": r.get("snippet", "")}
        for r in resp.json().get("webPages", {}).get("value", [])
    ]


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    providers = [
        ("tavily", _search_tavily),
        ("brave", _search_brave),
        ("serper", _search_serper),
        ("bing", _search_bing),
    ]
    for name, fn in providers:
        try:
            results = fn(query, max_results)
            if results:
                return results
        except Exception as exc:
            print(f"Search provider {name} error:", exc)
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


def _extract_locations(address: Optional[str]) -> List[str]:
    if not address:
        return []
    # Pick alphabetic tokens with length >= 3, excluding common generic words
    words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", address)
    generic = {"via", "loc", "piazza", "corso", "strada", "numero", "int", "telefono", "tel", "fax", "uff", "mag"}
    return [w for w in words if w.lower() not in generic]


def _result_relevance(result: Dict[str, str], contact: Contact, locations: List[str]) -> int:
    text = f"{result.get('title', '')} {result.get('snippet', '')} {result.get('url', '')}".lower()
    score = 0
    if contact.company and re.sub(r'[^a-z0-9]', '', contact.company.lower()) in re.sub(r'[^a-z0-9]', '', text):
        score += 10
    if contact.name and contact.name.lower().split() and all(part.lower() in text for part in contact.name.lower().split() if len(part) > 2):
        score += 8
    for loc in locations:
        if loc.lower() in text:
            score += 6
    if ".it" in result.get("url", ""):
        score += 4
    if "dubai" in text or "uae" in text or "emirates" in text:
        score -= 15
    if "linkedin.com" in result.get("url", "") and contact.company and contact.company.lower() in text:
        score += 5
    return max(score, 0)


def enrich_contact_data(contact: Contact) -> Dict[str, Any]:
    results = []
    company = contact.company or ""
    name = contact.name or ""
    locations = _extract_locations(contact.address)
    geo = " ".join(locations[:3])
    it_hint = "site:it" if not any(x in (contact.address or "").lower() for x in ["dubai", "uae", "usa", "uk"]) else ""

    if company:
        results.extend(search_web(f"{company} azienda sito ufficiale contatti {geo} {it_hint}", max_results=5))
        results.extend(search_web(f"{company} prodotti servizi settore {geo}", max_results=5))
        results.extend(search_web(f"{company} notizie premi eventi {geo}", max_results=4))
        results.extend(search_web(f"{company} {geo} linkedin instagram facebook", max_results=3))
    if name and company:
        results.extend(search_web(f"{name} {company} {geo} LinkedIn {it_hint}", max_results=5))
    elif name:
        results.extend(search_web(f"{name} {geo} LinkedIn {it_hint}", max_results=5))

    # deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    # score and filter out likely wrong matches
    scored = [(_result_relevance(r, contact, locations), r) for r in unique]
    scored.sort(key=lambda x: x[0], reverse=True)
    # Keep results with a minimum score, but always keep at least a few if available
    top = [r for _, r in scored if _result_relevance(r, contact, locations) >= 6]
    if len(top) < 3 and scored:
        top = [r for _, r in scored[:max(5, len(scored))]]

    snippets = "\n".join(r.get("snippet", "") for r in top)
    links = detect_social_links(snippets, top)
    confidence = "alta" if (company and locations) else ("media" if (company or locations) else "bassa")
    return {"results": top, "social_links": links, "confidence": confidence}


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


def _format_notes(notes: List[Any]) -> str:
    if not notes:
        return "Nessuna nota aggiuntiva."
    lines = []
    for n in notes:
        ntype = getattr(n, "note_type", "note") or "note"
        content = getattr(n, "content", "") or ""
        file_path = getattr(n, "file_path", "") or ""
        created = getattr(n, "created_at", "")
        item = f"[{ntype}] {created}: {content}"
        if file_path:
            item += f" (file: {os.path.basename(file_path)})"
        lines.append(item)
    return "\n".join(lines)


def generate_report(contact: Contact, enrichment: Dict[str, Any], company: CompanyProfile, notes: List[Any] = None) -> str:
    data = enrichment.get("results", [])
    social = enrichment.get("social_links", {})
    confidence = enrichment.get("confidence", "bassa")
    snippets = "\n".join(f"- {r.get('title', '')} ({r.get('url', '')}):\n  {r.get('snippet', '')}" for r in data)
    notes_text = _format_notes(notes or [])

    company_info = (
        f"Azienda proprietaria: {company.name or 'N/D'}\n"
        f"Descrizione: {company.description or 'N/D'}\n"
        f"Prodotti: {company.products or 'N/D'}\n"
        f"Servizi: {company.services or 'N/D'}\n"
        f"Valori: {company.values or 'N/D'}\n"
        f"Target: {company.target or 'N/D'}\n"
        f"Tono: {company.tone or 'professionale e cordiale'}\n"
    )

    confidence_note = (
        f"Affidabilità identificazione contatto: {confidence.upper()}. "
    )
    if confidence == "bassa":
        confidence_note += "Il biglietto non contiene azienda né sede, quindi i dati potrebbero riferirsi a un omonimo. Verifica sempre prima di contattare."
    elif confidence == "media":
        confidence_note += "Alcuni dati (azienda o sede) sono presenti, ma la verifica rimane consigliata."
    else:
        confidence_note += "Azienda e sede sono state trovate sul biglietto: l'identificazione è più affidabile."

    if openai_client:
        try:
            prompt = (
                "Sei un analista commerciale senior. Scrivi un report di analisi in italiano sul contatto e sulla sua azienda. "
                "NON scrivere una lettera di presentazione. Non usare frasi di cortesia. "
                f"{confidence_note}\n\n"
                "Organizza il testo in sezioni numerate con titoli chiari:\n\n"
                "1. AFFIDABILITÀ E AVVISO: ripeti il livello di affidabilità e spiega che bisogna verificare i dati se l'affidabilità è bassa.\n"
                "2. NOTE E STORIA DEL CONTATTO: riassumi eventuali appunti, contratti, telefonate o appuntamenti inseriti dall'utente. Usali per personalizzare l'approccio.\n"
                "3. PROFILO AZIENDA DEL CONTATTO: cosa fa l'azienda del contatto, settore, dimensione (se nota), tipo di clientela.\n"
                "4. PRODOTTI O SERVIZI DEL CONTATTO: elenca i prodotti/servizi principali che emergono dalle fonti, senza inventare.\n"
                "5. PRESENZA ONLINE: social trovati, sito web, eventuali recensioni o canali.\n"
                "6. DATI RILEVANTI: premi, pubblicazioni, eventi, partnership, certificazioni trovate.\n"
                "7. ANALISI MATCH CON I PRODOTTI DELL'AZIENDA PROPRIETARIA: confronta punto per punto i prodotti della nostra azienda con le esigenze del contatto e con la storia del rapporto. Sii specifico: indica quali prodotti potrebbero interessare e perché.\n"
                "8. APPROCCIO COMMERCIALE SUGGERITO: come contattarlo, che argomenti usare, eventuali obiezioni da anticipare.\n"
                "9. FONTI: elenca le fonti principali usate.\n\n"
                f"{company_info}\n"
                f"Nome contatto: {contact.name}\nAzienda contatto: {contact.company}\nRuolo: {contact.role}\n"
                f"Sito: {contact.website}\nLinkedIn: {contact.linkedin}\n\n"
                f"Social trovati: {json.dumps(social, ensure_ascii=False)}\n\n"
                f"Note e documenti del contatto:\n{notes_text}\n\n"
                f"Riferimenti web:\n{snippets}\n"
            )
            resp = openai_client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sei un analista commerciale che produce report strutturati sui contatti. Non sei un venditore: non scrivi lettere."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=900,
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
def upload_business_card(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file caricato")

    all_texts = []
    first_path = None
    for file in files:
        try:
            image_path = save_upload(file)
            if first_path is None:
                first_path = image_path
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

        try:
            text = run_ocr(image_path)
            all_texts.append(text)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

    raw_text = "\n\n".join(all_texts)
    fields = extract_fields(raw_text, image_path=first_path)
    contact = Contact(raw_text=raw_text, image_path=first_path, **fields)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_or_create_company_profile(db: Session) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if not profile:
        profile = CompanyProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@app.get("/config")
def get_config():
    plan = settings.plan.lower()
    features = ["capture", "export", "notes", "enrich", "report"]
    if plan in ("pro", "premium"):
        features.extend(["proposal", "whatsapp", "story", "email", "company_profile"])
    if plan == "premium":
        features.extend(["campaigns", "ads_calculator", "social_scheduler", "analytics"])
    return {
        "app_title": settings.app_title,
        "owner_name": settings.owner_name,
        "disable_auth": settings.disable_auth,
        "plan": plan,
        "features": features,
    }


@app.get("/company-profile", response_model=CompanyProfileOut)
def read_company_profile(db: Session = Depends(get_db)):
    return get_or_create_company_profile(db)


@app.put("/company-profile", response_model=CompanyProfileOut)
def update_company_profile(payload: CompanyProfileUpdate, db: Session = Depends(get_db)):
    profile = get_or_create_company_profile(db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


def fetch_website_text(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=15, headers=headers)
        r.raise_for_status()
        # Very basic tag stripping
        text = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]
    except Exception as exc:
        print("fetch website error:", exc)
    return ""


def enrich_company_profile_with_llm(website_text: str, url: str) -> dict:
    prompt = (
        "Analizza il testo di questo sito aziendale ed estrai le informazioni chiave. "
        "Restituisci SOLO un oggetto JSON con le chiavi: name, description, products, services, values, target, channels, website, email, phone, address, tone. "
        "products e services sono elenchi separati da virgola. "
        "channels è un elenco di canali di comunicazione (sito web, email, telefono, social). "
        "tone è un aggettivo che descrive il tono comunicativo (professionale, cordiale, informale, elegante, ecc.). "
        "Non scrivere testo fuori dal JSON.\n\n"
        f"URL: {url}\n\n{website_text}"
    )
    resp = openai_client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Sei un analista di siti aziendali. Restituisci solo JSON."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
    )
    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        if content.startswith("json"):
            content = content[4:].strip()
    parsed = json.loads(content)
    return {k: parsed.get(k) for k in ["name", "description", "products", "services", "values", "target", "channels", "website", "email", "phone", "address", "tone"]}


@app.post("/company-profile/enrich", response_model=CompanyProfileOut)
def enrich_company_profile(website: Optional[str] = None, db: Session = Depends(get_db)):
    profile = get_or_create_company_profile(db)
    url = website or profile.website or ""
    if not url:
        raise HTTPException(status_code=400, detail="Nessun sito web fornito")
    text = fetch_website_text(url)
    if not text:
        raise HTTPException(status_code=500, detail="Impossibile leggere il sito web")
    try:
        data = enrich_company_profile_with_llm(text, url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}") from exc
    for key, value in data.items():
        if value:
            setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@app.post("/contacts", response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    contact = Contact(**payload.model_dump(exclude_unset=True))
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@app.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, payload: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)
    return contact


@app.get("/contacts", response_model=List[ContactOut])
def list_contacts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()


@app.get("/contacts/export")
def export_contacts(format: str = "json", db: Session = Depends(get_db)):
    contacts = db.query(Contact).order_by(Contact.created_at.desc()).all()
    rows = [ContactOut.model_validate(c).model_dump() for c in contacts]
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        content = output.getvalue()
        return Response(content=content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=contacts.csv"})
    content = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
    return Response(content=content, media_type="application/json", headers={"Content-Disposition": "attachment; filename=contacts.json"})


@app.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return {"ok": True}


@app.get("/contacts/{contact_id}/notes", response_model=List[ContactNoteOut])
def list_contact_notes(contact_id: int, db: Session = Depends(get_db)):
    return db.query(ContactNote).filter(ContactNote.contact_id == contact_id).order_by(ContactNote.created_at.desc()).all()


@app.post("/contacts/{contact_id}/notes", response_model=ContactNoteOut)
def create_contact_note(contact_id: int, note_type: str = Form("note"), content: Optional[str] = Form(None), file: Optional[UploadFile] = File(None), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    file_path = None
    if file:
        file_path = save_upload(file)
    note = ContactNote(contact_id=contact_id, note_type=note_type, content=content or None, file_path=file_path)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.delete("/contacts/{contact_id}/notes/{note_id}")
def delete_contact_note(contact_id: int, note_id: int, db: Session = Depends(get_db)):
    note = db.query(ContactNote).filter(ContactNote.id == note_id, ContactNote.contact_id == contact_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"ok": True}


@app.post("/contacts/{contact_id}/enrich", response_model=ContactOut)
def enrich_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    company = get_or_create_company_profile(db)
    notes = db.query(ContactNote).filter(ContactNote.contact_id == contact_id).order_by(ContactNote.created_at.desc()).all()
    enrichment = enrich_contact_data(contact)
    contact.source_links = enrichment.get("results", [])
    contact.social_links = enrichment.get("social_links", {})
    contact.report = generate_report(contact, enrichment, company, notes)
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


# -------------------- Marketing Automation --------------------


def apply_template(text: str, contact: Contact) -> str:
    ctx = {
        "name": contact.name or "",
        "company": contact.company or "",
        "role": contact.role or "",
        "email": contact.email or "",
        "phone": contact.phone or "",
        "website": contact.website or "",
        "address": contact.address or "",
        "linkedin": contact.linkedin or "",
    }
    for key, value in ctx.items():
        text = text.replace(f"{{{key}}}", value)
    return text


def generate_with_llm(prompt: str, max_tokens: int = 800) -> str:
    if not openai_client:
        return ""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sei un esperto di marketing B2B. Scrivi in italiano."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        print("LLM generation error:", exc)
        return ""


def generate_content(contact: Contact, template: Template, kind: str, company: CompanyProfile, channel: Optional[str] = None) -> Dict[str, Any]:
    channel = channel or template.channel or "generic"
    base_body = apply_template(template.body, contact)
    subject = apply_template(template.subject or "", contact) if template.subject else None

    if openai_client:
        company_info = (
            f"Azienda proprietaria: {company.name or 'N/D'}\n"
            f"Descrizione: {company.description or 'N/D'}\n"
            f"Prodotti: {company.products or 'N/D'}\n"
            f"Servizi: {company.services or 'N/D'}\n"
            f"Valori: {company.values or 'N/D'}\n"
            f"Target: {company.target or 'N/D'}\n"
            f"Tono: {company.tone or 'professionale e cordiale'}\n"
        )
        prompt = (
            f"{company_info}\n"
            f"Tipo: {kind}\nCanale: {channel}\n"
            f"Destinatario: {contact.name} ({contact.role}) presso {contact.company}\n"
            f"Istruzioni: sei un commerciale dell'azienda proprietaria. Usa il testo seguente come base, "
            f"miglioralo e personalizzalo per il destinatario, promuovendo i prodotti/servizi dell'azienda proprietaria. "
            f"Mantieni il tono indicato.\n\nTesto base:\n{base_body}\n"
        )
        generated = generate_with_llm(prompt)
        if generated:
            body = generated
        else:
            body = base_body
    else:
        body = base_body

    return {"kind": kind, "channel": channel, "subject": subject, "body": body}


def match_filters(contact: Contact, filters: Optional[Dict[str, Any]]) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        attr = getattr(contact, key, None)
        if isinstance(value, list):
            if attr not in value:
                return False
        elif isinstance(value, dict):
            # support simple range filters { "min_score": 50 }
            if "min_score" in value and (contact.score or 0) < value["min_score"]:
                return False
        else:
            if attr != value:
                return False
    return True


@app.get("/templates", response_model=List[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(Template).order_by(Template.created_at.desc()).all()


@app.post("/templates", response_model=TemplateOut)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    tmpl = Template(**payload.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@app.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.query(Template).filter(Template.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@app.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, payload: TemplateUpdate, db: Session = Depends(get_db)):
    tmpl = db.query(Template).filter(Template.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tmpl, key, value)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@app.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.query(Template).filter(Template.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
    return {"ok": True}


@app.post("/contacts/{contact_id}/generate/{kind}", response_model=GeneratedContentOut)
def generate_for_contact(
    contact_id: int,
    kind: str,
    channel: Optional[str] = None,
    template_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if template_id:
        template = db.query(Template).filter(Template.id == template_id).first()
    else:
        template = db.query(Template).filter(Template.kind == kind, Template.is_default == 1).first()
        if not template:
            template = db.query(Template).filter(Template.kind == kind).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    company = get_or_create_company_profile(db)
    result = generate_content(contact, template, kind, company, channel)
    content = GeneratedContent(
        contact_id=contact.id,
        kind=result["kind"],
        channel=result["channel"],
        subject=result.get("subject"),
        body=result["body"],
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


@app.get("/mailing-list")
def get_mailing_list(
    tag: Optional[str] = None,
    min_score: Optional[int] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact)
    if tag:
        # naive JSON-like filter; works for small lists
        contacts = [c for c in query.all() if c.tags and tag in c.tags]
    else:
        contacts = query.all()
    if min_score is not None:
        contacts = [c for c in contacts if (c.score or 0) >= min_score]
    if company:
        contacts = [c for c in contacts if c.company and company.lower() in c.company.lower()]
    return [ContactOut.model_validate(c).model_dump() for c in contacts]


@app.post("/campaigns", response_model=CampaignOut)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/campaigns", response_model=List[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@app.post("/campaigns/{campaign_id}/run", response_model=List[GeneratedContentOut])
def run_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    template = None
    if campaign.template_id:
        template = db.query(Template).filter(Template.id == campaign.template_id).first()
    if not template:
        template = db.query(Template).filter(Template.kind == campaign.channel).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    contacts = db.query(Contact).all()
    generated = []
    for contact in contacts:
        if not match_filters(contact, campaign.filters):
            continue
        result = generate_content(contact, template, campaign.channel, campaign.channel)
        content = GeneratedContent(
            contact_id=contact.id,
            campaign_id=campaign.id,
            kind=result["kind"],
            channel=result["channel"],
            subject=result.get("subject"),
            body=result["body"],
        )
        db.add(content)
        generated.append(content)
    campaign.status = "ready"
    campaign.generated_count = len(generated)
    db.commit()
    for g in generated:
        db.refresh(g)
    return generated


@app.get("/generated-contents", response_model=List[GeneratedContentOut])
def list_generated_contents(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(GeneratedContent).order_by(GeneratedContent.created_at.desc()).offset(skip).limit(limit).all()


# -------------------- Premium: Social Post Drafts --------------------


def generate_social_post(media_path: str, platform: str, company: CompanyProfile) -> Dict[str, str]:
    """Generate a caption and hashtags from a photo/video."""
    if not openai_client:
        return {"caption": "", "hashtags": ""}
    image_b64 = None
    try:
        with Image.open(media_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((1200, 1200))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as exc:
        print("Image open error for social post:", exc)
    company_info = (
        f"Azienda: {company.name or 'N/D'}\n"
        f"Descrizione: {company.description or 'N/D'}\n"
        f"Prodotti: {company.products or 'N/D'}\n"
        f"Valori: {company.values or 'N/D'}\n"
        f"Tono: {company.tone or 'professionale e cordiale'}\n"
    )
    user_content: List[Dict[str, Any]] = [
        {"type": "text", "text": (
            f"Scrivi una didascalia per un post {platform} in italiano, basata su questa immagine/video. "
            "Includi un titolo accattivante, una breve descrizione, un invito all'azione e 5-10 hashtag rilevanti. "
            "Restituisci SOLO un oggetto JSON con chiavi 'caption' e 'hashtags'. Non scrivere testo fuori dal JSON.\n\n"
            f"{company_info}"
        )},
    ]
    if image_b64:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
    try:
        resp = openai_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sei un social media manager per aziende agricole e artigianali italiane. Restituisci solo JSON."},
                {"role": "user", "content": user_content},
            ],
            max_tokens=500,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
            if content.startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        return {"caption": parsed.get("caption", ""), "hashtags": parsed.get("hashtags", "")}
    except Exception as exc:
        print("Social post generation error:", exc)
    return {"caption": "", "hashtags": ""}


@app.post("/social-posts", response_model=SocialPostOut)
def create_social_post(platform: str = Form("instagram"), media_type: str = Form("image"), file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file and file.filename:
        file_path = save_upload(file)
    else:
        raise HTTPException(status_code=400, detail="Nessun file caricato")
    company = get_or_create_company_profile(db)
    generated = generate_social_post(file_path, platform, company)
    post = SocialPost(
        media_path=file_path,
        media_type=media_type,
        platform=platform,
        caption=generated.get("caption"),
        hashtags=generated.get("hashtags"),
        status="draft",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/social-posts", response_model=List[SocialPostOut])
def list_social_posts(db: Session = Depends(get_db)):
    return db.query(SocialPost).order_by(SocialPost.created_at.desc()).all()


@app.put("/social-posts/{post_id}", response_model=SocialPostOut)
def update_social_post(post_id: int, payload: SocialPostCreate, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, key, value)
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@app.post("/social-posts/{post_id}/approve", response_model=SocialPostOut)
def approve_social_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = "approved"
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@app.delete("/social-posts/{post_id}")
def delete_social_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"ok": True}


# -------------------- Social Credentials & Publishing --------------------


@app.post("/social-credentials", response_model=SocialCredentialOut)
def create_social_credential(payload: SocialCredentialCreate, db: Session = Depends(get_db)):
    extra = None
    if payload.extra:
        try:
            extra_dict = json.loads(payload.extra)
            extra = json.dumps(extra_dict)
        except Exception:
            extra = payload.extra
    cred = SocialCredential(
        platform=payload.platform,
        label=payload.label,
        access_token=payload.access_token,
        extra=extra,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


@app.get("/social-credentials", response_model=List[SocialCredentialOut])
def list_social_credentials(platform: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(SocialCredential)
    if platform:
        q = q.filter(SocialCredential.platform == platform)
    return q.order_by(SocialCredential.created_at.desc()).all()


@app.delete("/social-credentials/{cred_id}")
def delete_social_credential(cred_id: int, db: Session = Depends(get_db)):
    cred = db.query(SocialCredential).filter(SocialCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(cred)
    db.commit()
    return {"ok": True}


def _publish_telegram(cred: SocialCredential, text: str, media_path: Optional[str]) -> Dict[str, Any]:
    extra = json.loads(cred.extra or "{}")
    chat_id = extra.get("chat_id")
    if not chat_id:
        raise ValueError("chat_id mancante nelle credenziali Telegram")
    token = cred.access_token
    if media_path and os.path.exists(media_path):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(media_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": text, "parse_mode": "HTML"}
            r = requests.post(url, data=data, files=files, timeout=30)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, json=data, timeout=30)
    r.raise_for_status()
    return r.json()


def _publish_facebook(cred: SocialCredential, text: str, media_path: Optional[str]) -> Dict[str, Any]:
    extra = json.loads(cred.extra or "{}")
    page_id = extra.get("page_id")
    if not page_id:
        raise ValueError("page_id mancante nelle credenziali Facebook")
    token = cred.access_token
    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    if media_path and os.path.exists(media_path):
        with open(media_path, "rb") as f:
            files = {"file": f}
            data = {"message": text, "access_token": token}
            r = requests.post(url, data=data, files=files, timeout=30)
    else:
        data = {"message": text, "access_token": token}
        r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()


def _publish_whatsapp(cred: SocialCredential, text: str) -> Dict[str, Any]:
    extra = json.loads(cred.extra or "{}")
    phone_number_id = extra.get("phone_number_id")
    to = extra.get("to")
    if not phone_number_id or not to:
        raise ValueError("phone_number_id o to mancanti nelle credenziali WhatsApp")
    token = cred.access_token
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    r = requests.post(url, json=data, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return r.json()


@app.post("/social-posts/{post_id}/publish")
def publish_social_post(post_id: int, credential_id: Optional[int] = None, db: Session = Depends(get_db)):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.caption:
        raise HTTPException(status_code=400, detail="Nessuna didascalia da pubblicare")

    q = db.query(SocialCredential).filter(SocialCredential.platform == post.platform)
    if credential_id:
        q = q.filter(SocialCredential.id == credential_id)
    cred = q.first()
    if not cred:
        raise HTTPException(status_code=400, detail=f"Nessuna credenziale salvata per {post.platform}")

    text = f"{post.caption}\n\n{post.hashtags or ''}".strip()
    try:
        if post.platform == "telegram":
            result = _publish_telegram(cred, text, post.media_path)
        elif post.platform in ("facebook", "instagram"):
            result = _publish_facebook(cred, text, post.media_path)
        elif post.platform == "whatsapp":
            result = _publish_whatsapp(cred, text)
        else:
            raise ValueError(f"Piattaforma {post.platform} non supportata per la pubblicazione automatica")
        post.status = "published"
        status = "success"
        message = json.dumps(result)
    except Exception as exc:
        status = "error"
        message = str(exc)
    post.updated_at = datetime.utcnow()
    db.add(SocialPublishLog(social_post_id=post.id, platform=post.platform, status=status, message=message))
    db.commit()
    db.refresh(post)
    if status == "error":
        raise HTTPException(status_code=500, detail=message)
    return {"ok": True, "post": SocialPostOut.from_orm(post), "result": json.loads(message)}


@app.get("/health")
def health():
    return {"status": "ok"}


if os.path.exists("/app/frontend"):
    app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
