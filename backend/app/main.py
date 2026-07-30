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
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
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
    clearbit_api_key: Optional[str] = None
    uploads_dir: str = "/app/data/uploads"
    app_title: str = "DiSpace Lead Capture"
    owner_name: str = ""

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


def generate_report(contact: Contact, enrichment: Dict[str, Any], company: CompanyProfile) -> str:
    data = enrichment.get("results", [])
    social = enrichment.get("social_links", {})
    snippets = "\n".join(f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in data[:5])

    company_info = (
        f"Azienda proprietaria: {company.name or 'N/D'}\n"
        f"Descrizione: {company.description or 'N/D'}\n"
        f"Prodotti: {company.products or 'N/D'}\n"
        f"Servizi: {company.services or 'N/D'}\n"
        f"Valori: {company.values or 'N/D'}\n"
        f"Target: {company.target or 'N/D'}\n"
        f"Tono: {company.tone or 'professionale e cordiale'}\n"
    )

    if openai_client:
        try:
            prompt = (
                "Sei un consulente commerciale per l'azienda descritta sopra. "
                "Genera un report sintetico in italiano sul contatto, evidenziando come "
                "i prodotti/servizi dell'azienda possono interessare questo contatto. "
                "Massimo 300 parole.\n\n"
                f"{company_info}\n"
                f"Nome: {contact.name}\nAzienda: {contact.company}\nRuolo: {contact.role}\n"
                f"Sito: {contact.website}\nLinkedIn: {contact.linkedin}\n\n"
                f"Riferimenti:\n{snippets}\n"
            )
            resp = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sei un assistente commerciale che vende i prodotti dell'azienda proprietaria."},
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
    return {"app_title": settings.app_title, "owner_name": settings.owner_name, "disable_auth": settings.disable_auth}


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


@app.post("/contacts/{contact_id}/enrich", response_model=ContactOut)
def enrich_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    company = get_or_create_company_profile(db)
    enrichment = enrich_contact_data(contact)
    contact.source_links = enrichment.get("results", [])
    contact.social_links = enrichment.get("social_links", {})
    contact.report = generate_report(contact, enrichment, company)
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


@app.get("/health")
def health():
    return {"status": "ok"}


if os.path.exists("/app/frontend"):
    app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
