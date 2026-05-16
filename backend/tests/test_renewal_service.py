from datetime import date, timedelta

from app.schemas import Prescription
from app.services.renewal_service import RenewalService


def test_marks_renewal_when_stock_is_low() -> None:
    service = RenewalService()
    today = date(2026, 5, 10)
    prescriptions = [
        Prescription(
            id="rx-1",
            medication_name="Test",
            prescribed_daily_dose=2,
            package_size=10,
            remaining_packages=2,
            valid_until=today + timedelta(days=100),
        )
    ]

    result = service.build_advice(prescriptions, as_of=today)

    assert result[0].renewal_needed is True
    assert result[0].estimated_days_left == 10


def test_includes_issued_by_when_renewal_needed() -> None:
    service = RenewalService()
    today = date(2026, 5, 10)
    prescriptions = [
        Prescription(
            id="rx-issued",
            medication_name="Test Utfardad",
            prescriber_name="Göran Heden",
            prescriber_organization="SLSO, Psykiatri Södra Stockholm",
            prescribed_daily_dose=1,
            package_size=10,
            remaining_packages=0,
            valid_until=today + timedelta(days=200),
        )
    ]

    result = service.build_advice(prescriptions, as_of=today)

    assert result[0].renewal_needed is True
    assert result[0].issued_by == "Göran Heden, SLSO, Psykiatri Södra Stockholm"


def test_marks_renewal_when_validity_is_ending() -> None:
    service = RenewalService()
    today = date(2026, 5, 10)
    prescriptions = [
        Prescription(
            id="rx-2",
            medication_name="Test 2",
            prescribed_daily_dose=1,
            package_size=30,
            remaining_packages=2,
            valid_until=today + timedelta(days=10),
        )
    ]

    result = service.build_advice(prescriptions, as_of=today)

    assert result[0].renewal_needed is True
    assert result[0].days_until_validity_ends == 10


def test_keeps_status_green_when_not_needed() -> None:
    service = RenewalService()
    today = date(2026, 5, 10)
    prescriptions = [
        Prescription(
            id="rx-3",
            medication_name="Test 3",
            prescribed_daily_dose=1,
            package_size=100,
            remaining_packages=2,
            valid_until=today + timedelta(days=200),
        )
    ]

    result = service.build_advice(prescriptions, as_of=today)

    assert result[0].renewal_needed is False
    assert result[0].reason == "Ingen åtgärd behövs ännu"


def test_marks_renewal_when_active_prescription_missing() -> None:
    service = RenewalService()
    today = date(2026, 5, 10)
    prescriptions = [
        Prescription(
            id="historic-1",
            medication_name="Historiskt Lakemedel",
            prescribed_daily_dose=1,
            package_size=30,
            remaining_packages=0,
            valid_until=today,
            has_active_prescription=False,
        )
    ]

    result = service.build_advice(prescriptions, as_of=today)

    assert result[0].renewal_needed is True
    assert result[0].estimated_days_left == 0
    assert result[0].reason == "Inget aktivt recept hittades, förnyelse behövs"
