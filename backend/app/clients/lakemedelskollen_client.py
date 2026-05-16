from datetime import date
from datetime import datetime
from typing import Any

import httpx

from ..config import settings
from ..schemas import Prescription


class LakemedelskollenIntegrationError(Exception):
    pass


class LakemedelskollenClient:
    """Boundary mot extern tjanst."""

    def __init__(self) -> None:
        self._base_url = settings.lakemedelskollen_base_url.rstrip("/")

    @staticmethod
    def _parse_administration_times(raw_times: Any) -> list[str]:
        if isinstance(raw_times, list):
            return [str(value).strip() for value in raw_times if str(value).strip()]
        if isinstance(raw_times, str):
            return [value.strip() for value in raw_times.split(",") if value.strip()]
        return []

    @staticmethod
    def _parse_date(raw_date: str | None) -> date:
        if not raw_date:
            raise LakemedelskollenIntegrationError("Saknar giltighetsdatum i extern payload")

        for parser in (date.fromisoformat, lambda v: datetime.strptime(v, "%Y-%m-%dT%H:%M:%S").date()):
            try:
                return parser(raw_date)
            except ValueError:
                continue
        raise LakemedelskollenIntegrationError("Ogiltigt datumformat i extern payload")

    def _map_external_prescription(self, item: dict[str, Any]) -> Prescription:
        try:
            prescription_id = str(item.get("id") or item.get("prescriptionId"))
            prescribed_product_raw = (
                item.get("prescribedMedication")
                or item.get("prescribedProduct")
                or item.get("prescribedDrug")
                or item.get("medicationName")
                or item.get("name")
            )
            medication_name = str(prescribed_product_raw)
            prescribed_daily_dose = float(item.get("prescribedDailyDose") or item.get("dailyDose"))
            package_size = int(item.get("packageSize") or item.get("unitsPerPackage"))
            remaining_packages = int(item.get("remainingPackages") or item.get("packagesLeft") or 0)
            valid_until = self._parse_date(item.get("validUntil") or item.get("expiryDate"))
        except (TypeError, ValueError) as exc:
            raise LakemedelskollenIntegrationError("Ogiltig datatyp i extern payload") from exc

        if not prescription_id or not medication_name:
            raise LakemedelskollenIntegrationError("Saknar obligatoriska falt i extern payload")

        dose_per_intake_raw = item.get("dosePerIntake") or item.get("singleDose")
        dose_per_intake = float(dose_per_intake_raw) if dose_per_intake_raw is not None else None
        dose_unit_raw = item.get("doseUnit") or item.get("unit")
        dose_unit = str(dose_unit_raw).strip() if dose_unit_raw else None
        administration_times = self._parse_administration_times(
            item.get("administrationTimes") or item.get("timesOfDay")
        )
        instruction_raw = item.get("instructionText") or item.get("dosageInstruction")
        instruction_text = str(instruction_raw).strip() if instruction_raw else None
        active_substance_raw = item.get("activeSubstance") or item.get("substance")
        active_substance = str(active_substance_raw).strip() if active_substance_raw else None
        prescribed_product = str(prescribed_product_raw).strip() if prescribed_product_raw else None

        return Prescription(
            id=prescription_id,
            medication_name=medication_name,
            active_substance=active_substance,
            prescribed_product=prescribed_product,
            prescribed_daily_dose=prescribed_daily_dose,
            package_size=package_size,
            remaining_packages=remaining_packages,
            valid_until=valid_until,
            dose_per_intake=dose_per_intake,
            dose_unit=dose_unit,
            administration_times=administration_times,
            instruction_text=instruction_text,
            has_active_prescription=bool(item.get("hasActivePrescription", True)),
        )

    def _fetch_external_prescriptions(self, personnummer: str) -> list[Prescription]:
        if not settings.lakemedelskollen_api_token:
            raise LakemedelskollenIntegrationError("Saknar API-token for Lakemedelskollen")

        url = f"{self._base_url}{settings.lakemedelskollen_prescriptions_path}"
        headers = {
            "Authorization": f"Bearer {settings.lakemedelskollen_api_token}",
            "Accept": "application/json",
        }
        params = {"personnummer": personnummer}

        try:
            with httpx.Client(timeout=settings.lakemedelskollen_timeout_seconds) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise LakemedelskollenIntegrationError("Timeout mot Lakemedelskollen") from exc
        except httpx.HTTPStatusError as exc:
            raise LakemedelskollenIntegrationError("Lakemedelskollen returnerade felstatus") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise LakemedelskollenIntegrationError("Kunde inte lasa svar fran Lakemedelskollen") from exc

        data = payload.get("prescriptions") if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            raise LakemedelskollenIntegrationError("Ogiltigt payload-format fran Lakemedelskollen")

        return [self._map_external_prescription(item) for item in data if isinstance(item, dict)]

    def get_prescriptions_for_patient(self, personnummer: str) -> list[Prescription]:
        if not settings.lakemedelskollen_direct_enabled:
            return []
        return self._fetch_external_prescriptions(personnummer)
