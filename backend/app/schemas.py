from datetime import date

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    personnummer: str = Field(..., description="YYYYMMDDNNNN eller YYMMDDNNNN")

    @field_validator("personnummer")
    @classmethod
    def validate_personnummer(cls, value: str) -> str:
        digits = value.replace("-", "")
        if not digits.isdigit() or len(digits) not in {10, 12}:
            raise ValueError("Ogiltigt personnummerformat")
        return digits


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Prescription(BaseModel):
    id: str
    medication_name: str
    active_substance: str | None = None
    prescribed_product: str | None = None
    dispensed_product: str | None = None
    prescriber_name: str | None = None
    prescriber_organization: str | None = None
    prescriber_location: str | None = None
    prescriber_phone: str | None = None
    prescribed_daily_dose: float = Field(gt=0)
    package_size: int = Field(gt=0)
    remaining_packages: int = Field(ge=0)
    valid_until: date
    latest_dispense_date: date | None = None
    refill_remaining: int | None = Field(default=None, ge=0)
    refill_total: int | None = Field(default=None, ge=0)
    package_text: str | None = None
    minimum_interval_text: str | None = None
    next_benefit_dispense_date: date | None = None
    subsidy_eligible: bool | None = None
    dose_per_intake: float | None = Field(default=None, gt=0)
    dose_unit: str | None = None
    administration_times: list[str] = Field(default_factory=list)
    instruction_text: str | None = None
    has_active_prescription: bool = True
    source_printed_at: str | None = None
    source_high_cost_period_end: date | None = None
    raw_prescription_text: str | None = None


class RenewalAdvice(BaseModel):
    prescription_id: str
    medication_name: str
    estimated_days_left: int
    days_until_validity_ends: int
    renewal_needed: bool
    reason: str
    issued_by: str | None = None


class RenewalAdviceList(BaseModel):
    advice: list[RenewalAdvice]


class UploadScrapeResponse(BaseModel):
    imported_prescriptions: int
    total_prescriptions: int
    detected_personnummer: str | None = None


class ManualMedicationRequest(BaseModel):
    medication_name: str = Field(..., min_length=2, max_length=160)

    @field_validator("medication_name")
    @classmethod
    def validate_medication_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Läkemedelsnamn måste innehålla minst 2 tecken")
        return normalized
