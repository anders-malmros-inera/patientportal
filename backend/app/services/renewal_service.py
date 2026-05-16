from datetime import date

from ..schemas import Prescription, RenewalAdvice


class RenewalService:
    @staticmethod
    def _build_issued_by(item: Prescription) -> str | None:
        parts = [part for part in [item.prescriber_name, item.prescriber_organization] if part]
        if not parts:
            return None
        return ", ".join(parts)

    def build_advice(self, prescriptions: list[Prescription], as_of: date | None = None) -> list[RenewalAdvice]:
        today = as_of or date.today()
        advice: list[RenewalAdvice] = []

        for item in prescriptions:
            if not item.has_active_prescription:
                advice.append(
                    RenewalAdvice(
                        prescription_id=item.id,
                        medication_name=item.medication_name,
                        estimated_days_left=0,
                        days_until_validity_ends=0,
                        renewal_needed=True,
                        reason="Inget aktivt recept hittades, förnyelse behövs",
                        issued_by=self._build_issued_by(item),
                    )
                )
                continue

            estimated_days_left = int((item.package_size * item.remaining_packages) / item.prescribed_daily_dose)
            days_until_validity_ends = (item.valid_until - today).days

            should_renew_stock = estimated_days_left <= 14
            should_renew_validity = days_until_validity_ends <= 30
            renewal_needed = should_renew_stock or should_renew_validity

            if should_renew_stock and should_renew_validity:
                reason = "Lågt lager och receptet går snart ut"
            elif should_renew_stock:
                reason = "Få dagar kvar av läkemedlet"
            elif should_renew_validity:
                reason = "Receptets giltighet går ut inom 30 dagar"
            else:
                reason = "Ingen åtgärd behövs ännu"

            advice.append(
                RenewalAdvice(
                    prescription_id=item.id,
                    medication_name=item.medication_name,
                    estimated_days_left=estimated_days_left,
                    days_until_validity_ends=days_until_validity_ends,
                    renewal_needed=renewal_needed,
                    reason=reason,
                    issued_by=self._build_issued_by(item) if renewal_needed else None,
                )
            )

        return advice
