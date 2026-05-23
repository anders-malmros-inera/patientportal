import io
import re
from datetime import date

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from .clients.lakemedelskollen_client import LakemedelskollenClient, LakemedelskollenIntegrationError
from .config import settings
from .database import (
    delete_prescription,
    init_db,
    load_prescriptions,
    save_prescriptions,
    save_scrape_document,
)
from .dependencies import get_current_patient
from .schemas import (
    LoginRequest,
    ManualMedicationRequest,
    Prescription,
    RenewalAdviceList,
    TokenResponse,
    UploadScrapeResponse,
)
from .security import create_access_token
from .services.renewal_service import RenewalService
from .services.scrape_parser_service import ScrapeParserService

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

prescription_client = LakemedelskollenClient()
renewal_service = RenewalService()
scrape_parser = ScrapeParserService()


def _merge_prescriptions(current: list[Prescription], historical: list[Prescription]) -> list[Prescription]:
    current_by_name = {item.medication_name.casefold(): item for item in current}
    merged = list(current)

    for item in historical:
        key = item.medication_name.casefold()
        if key in current_by_name:
            continue

        merged.append(
            item.model_copy(
                update={
                    "id": item.id or f"historical-{key}",
                    "remaining_packages": 0,
                    "has_active_prescription": False,
                }
            )
        )

    return merged


def _get_and_persist_prescriptions(personnummer: str) -> list[Prescription]:
    historical = load_prescriptions(personnummer)

    if not settings.lakemedelskollen_direct_enabled:
        return historical

    current = prescription_client.get_prescriptions_for_patient(personnummer)

    merged = _merge_prescriptions(current, historical)
    save_prescriptions(personnummer, merged)
    return merged


def _matches_patient(uploaded_personnummer: str | None, current_personnummer: str) -> bool:
    if uploaded_personnummer is None:
        return True

    digits = uploaded_personnummer.strip()
    if len(digits) == 8:
        return current_personnummer.startswith(digits)
    if len(digits) == 10:
        return current_personnummer.endswith(digits)
    if len(digits) == 12:
        return current_personnummer == digits
    return False


def _extract_text_from_upload(file_name: str | None, raw_content: bytes) -> str:
    lower_name = (file_name or "").casefold()
    if lower_name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(raw_content))
            extracted = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kunde inte läsa PDF-filen. Kontrollera att filen inte är skadad.",
            ) from exc

        if not extracted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF-filen innehåller ingen läsbar text. Prova annan export eller OCR.",
            )
        return extracted

    try:
        return raw_content.decode("utf-8")
    except UnicodeDecodeError:
        return raw_content.decode("latin-1", errors="ignore")


def _build_manual_medication_id(medication_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", medication_name.casefold()).strip("-") or "med"
    return f"manual-{slug}-{date.today().isoformat()}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.post(f"{settings.api_prefix}/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    access_token = create_access_token(payload.personnummer)
    return TokenResponse(access_token=access_token)


@app.get(f"{settings.api_prefix}/prescriptions", response_model=list[Prescription])
def get_prescriptions(personnummer: str = Depends(get_current_patient)) -> list[Prescription]:
    try:
        return _get_and_persist_prescriptions(personnummer)
    except LakemedelskollenIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunde inte hamta recept fran Lakemedelskollen",
        ) from exc


@app.post(f"{settings.api_prefix}/prescriptions/manual", response_model=Prescription)
def add_manual_medication(
    payload: ManualMedicationRequest,
    personnummer: str = Depends(get_current_patient),
) -> Prescription:
    existing = load_prescriptions(personnummer)
    requested_name = payload.medication_name.casefold()

    for item in existing:
        if item.medication_name.casefold() == requested_name:
            return item

    manual_medication = Prescription(
        id=_build_manual_medication_id(payload.medication_name),
        medication_name=payload.medication_name,
        prescribed_product=payload.medication_name,
        prescribed_daily_dose=1.0,
        package_size=1,
        remaining_packages=0,
        valid_until=date.today(),
        has_active_prescription=False,
        instruction_text="Manuellt tillagd utan recept",
    )

    save_prescriptions(personnummer, [*existing, manual_medication])
    return manual_medication


@app.delete(f"{settings.api_prefix}/prescriptions/{{prescription_id}}", status_code=status.HTTP_204_NO_CONTENT)
def remove_prescription(prescription_id: str, personnummer: str = Depends(get_current_patient)) -> Response:
    removed = delete_prescription(personnummer, prescription_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receptet hittades inte")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(f"{settings.api_prefix}/renewal-advice", response_model=RenewalAdviceList)
def get_renewal_advice(personnummer: str = Depends(get_current_patient)) -> RenewalAdviceList:
    try:
        prescriptions = _get_and_persist_prescriptions(personnummer)
    except LakemedelskollenIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Kunde inte hamta recept fran Lakemedelskollen",
        ) from exc
    advice = renewal_service.build_advice(prescriptions)
    return RenewalAdviceList(advice=advice)


@app.post(f"{settings.api_prefix}/prescriptions/upload-scrape", response_model=UploadScrapeResponse)
async def upload_scrape_prescriptions(
    file: UploadFile = File(...),
    personnummer: str = Depends(get_current_patient),
) -> UploadScrapeResponse:
    raw_content = await file.read()
    text = _extract_text_from_upload(file.filename, raw_content)

    try:
        parsed = scrape_parser.parse(text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not _matches_patient(parsed.personnummer, personnummer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filen verkar tillhöra ett annat personnummer",
        )

    historical = load_prescriptions(personnummer)
    merged = _merge_prescriptions(parsed.prescriptions, historical)
    save_prescriptions(personnummer, merged)
    save_scrape_document(
        personnummer=personnummer,
        source_filename=file.filename,
        detected_personnummer=parsed.personnummer,
        printed_at=parsed.printed_at,
        high_cost_period_end=parsed.high_cost_period_end,
        raw_document_text=parsed.raw_document_text,
    )

    return UploadScrapeResponse(
        imported_prescriptions=len(parsed.prescriptions),
        total_prescriptions=len(merged),
        detected_personnummer=parsed.personnummer,
    )
