import sqlite3
from datetime import date
from pathlib import Path

from .schemas import Prescription

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "patientportal.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    if column_name in _table_columns(connection, table_name):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_prescriptions (
                personnummer TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                prescription_id TEXT NOT NULL,
                prescribed_daily_dose REAL NOT NULL,
                package_size INTEGER NOT NULL,
                remaining_packages INTEGER NOT NULL,
                valid_until TEXT NOT NULL,
                dose_per_intake REAL NULL,
                dose_unit TEXT NULL,
                administration_times TEXT NULL,
                instruction_text TEXT NULL,
                has_active_prescription INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (personnummer, medication_name)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_documents (
                personnummer TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                source_filename TEXT NULL,
                detected_personnummer TEXT NULL,
                printed_at TEXT NULL,
                high_cost_period_end TEXT NULL,
                raw_document_text TEXT NOT NULL
            )
            """
        )
        _ensure_column(connection, "patient_prescriptions", "active_substance", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "prescribed_product", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "dispensed_product", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "prescriber_name", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "prescriber_organization", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "prescriber_location", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "prescriber_phone", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "latest_dispense_date", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "refill_remaining", "INTEGER NULL")
        _ensure_column(connection, "patient_prescriptions", "refill_total", "INTEGER NULL")
        _ensure_column(connection, "patient_prescriptions", "package_text", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "minimum_interval_text", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "next_benefit_dispense_date", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "subsidy_eligible", "INTEGER NULL")
        _ensure_column(connection, "patient_prescriptions", "source_printed_at", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "source_high_cost_period_end", "TEXT NULL")
        _ensure_column(connection, "patient_prescriptions", "raw_prescription_text", "TEXT NULL")


def save_prescriptions(personnummer: str, prescriptions: list[Prescription]) -> None:
    init_db()
    today = date.today().isoformat()
    with _connect() as connection:
        for item in prescriptions:
            administration_times = ",".join(item.administration_times)
            connection.execute(
                """
                INSERT INTO patient_prescriptions (
                    personnummer,
                    medication_name,
                    prescription_id,
                    active_substance,
                    prescribed_product,
                    dispensed_product,
                    prescriber_name,
                    prescriber_organization,
                    prescriber_location,
                    prescriber_phone,
                    prescribed_daily_dose,
                    package_size,
                    remaining_packages,
                    valid_until,
                    latest_dispense_date,
                    refill_remaining,
                    refill_total,
                    package_text,
                    minimum_interval_text,
                    next_benefit_dispense_date,
                    subsidy_eligible,
                    dose_per_intake,
                    dose_unit,
                    administration_times,
                    instruction_text,
                    has_active_prescription,
                    source_printed_at,
                    source_high_cost_period_end,
                    raw_prescription_text,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(personnummer, medication_name)
                DO UPDATE SET
                    prescription_id=excluded.prescription_id,
                    active_substance=excluded.active_substance,
                    prescribed_product=excluded.prescribed_product,
                    dispensed_product=excluded.dispensed_product,
                    prescriber_name=excluded.prescriber_name,
                    prescriber_organization=excluded.prescriber_organization,
                    prescriber_location=excluded.prescriber_location,
                    prescriber_phone=excluded.prescriber_phone,
                    prescribed_daily_dose=excluded.prescribed_daily_dose,
                    package_size=excluded.package_size,
                    remaining_packages=excluded.remaining_packages,
                    valid_until=excluded.valid_until,
                    latest_dispense_date=excluded.latest_dispense_date,
                    refill_remaining=excluded.refill_remaining,
                    refill_total=excluded.refill_total,
                    package_text=excluded.package_text,
                    minimum_interval_text=excluded.minimum_interval_text,
                    next_benefit_dispense_date=excluded.next_benefit_dispense_date,
                    subsidy_eligible=excluded.subsidy_eligible,
                    dose_per_intake=excluded.dose_per_intake,
                    dose_unit=excluded.dose_unit,
                    administration_times=excluded.administration_times,
                    instruction_text=excluded.instruction_text,
                    has_active_prescription=excluded.has_active_prescription,
                    source_printed_at=excluded.source_printed_at,
                    source_high_cost_period_end=excluded.source_high_cost_period_end,
                    raw_prescription_text=excluded.raw_prescription_text,
                    updated_at=excluded.updated_at
                """,
                (
                    personnummer,
                    item.medication_name,
                    item.id,
                    item.active_substance,
                    item.prescribed_product,
                    item.dispensed_product,
                    item.prescriber_name,
                    item.prescriber_organization,
                    item.prescriber_location,
                    item.prescriber_phone,
                    item.prescribed_daily_dose,
                    item.package_size,
                    item.remaining_packages,
                    item.valid_until.isoformat(),
                    item.latest_dispense_date.isoformat() if item.latest_dispense_date else None,
                    item.refill_remaining,
                    item.refill_total,
                    item.package_text,
                    item.minimum_interval_text,
                    item.next_benefit_dispense_date.isoformat() if item.next_benefit_dispense_date else None,
                    None if item.subsidy_eligible is None else (1 if item.subsidy_eligible else 0),
                    item.dose_per_intake,
                    item.dose_unit,
                    administration_times,
                    item.instruction_text,
                    1 if item.has_active_prescription else 0,
                    item.source_printed_at,
                    item.source_high_cost_period_end.isoformat() if item.source_high_cost_period_end else None,
                    item.raw_prescription_text,
                    today,
                ),
            )


def load_prescriptions(personnummer: str) -> list[Prescription]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                prescription_id,
                medication_name,
                active_substance,
                prescribed_product,
                dispensed_product,
                prescriber_name,
                prescriber_organization,
                prescriber_location,
                prescriber_phone,
                prescribed_daily_dose,
                package_size,
                remaining_packages,
                valid_until,
                latest_dispense_date,
                refill_remaining,
                refill_total,
                package_text,
                minimum_interval_text,
                next_benefit_dispense_date,
                subsidy_eligible,
                dose_per_intake,
                dose_unit,
                administration_times,
                instruction_text,
                has_active_prescription,
                source_printed_at,
                source_high_cost_period_end,
                raw_prescription_text
            FROM patient_prescriptions
            WHERE personnummer = ?
            """,
            (personnummer,),
        ).fetchall()

    result: list[Prescription] = []
    for row in rows:
        times_raw = row["administration_times"] or ""
        administration_times = [value.strip() for value in times_raw.split(",") if value.strip()]
        result.append(
            Prescription(
                id=row["prescription_id"],
                medication_name=row["medication_name"],
                active_substance=row["active_substance"],
                prescribed_product=row["prescribed_product"],
                dispensed_product=row["dispensed_product"],
                prescriber_name=row["prescriber_name"],
                prescriber_organization=row["prescriber_organization"],
                prescriber_location=row["prescriber_location"],
                prescriber_phone=row["prescriber_phone"],
                prescribed_daily_dose=float(row["prescribed_daily_dose"]),
                package_size=int(row["package_size"]),
                remaining_packages=int(row["remaining_packages"]),
                valid_until=date.fromisoformat(row["valid_until"]),
                latest_dispense_date=date.fromisoformat(row["latest_dispense_date"]) if row["latest_dispense_date"] else None,
                refill_remaining=int(row["refill_remaining"]) if row["refill_remaining"] is not None else None,
                refill_total=int(row["refill_total"]) if row["refill_total"] is not None else None,
                package_text=row["package_text"],
                minimum_interval_text=row["minimum_interval_text"],
                next_benefit_dispense_date=(
                    date.fromisoformat(row["next_benefit_dispense_date"]) if row["next_benefit_dispense_date"] else None
                ),
                subsidy_eligible=(None if row["subsidy_eligible"] is None else bool(row["subsidy_eligible"])),
                dose_per_intake=float(row["dose_per_intake"]) if row["dose_per_intake"] is not None else None,
                dose_unit=row["dose_unit"],
                administration_times=administration_times,
                instruction_text=row["instruction_text"],
                has_active_prescription=bool(row["has_active_prescription"]),
                source_printed_at=row["source_printed_at"],
                source_high_cost_period_end=(
                    date.fromisoformat(row["source_high_cost_period_end"]) if row["source_high_cost_period_end"] else None
                ),
                raw_prescription_text=row["raw_prescription_text"],
            )
        )
    return result


def save_scrape_document(
    personnummer: str,
    source_filename: str | None,
    detected_personnummer: str | None,
    printed_at: str | None,
    high_cost_period_end: date | None,
    raw_document_text: str,
) -> None:
    init_db()
    uploaded_at = date.today().isoformat()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO scrape_documents (
                personnummer,
                uploaded_at,
                source_filename,
                detected_personnummer,
                printed_at,
                high_cost_period_end,
                raw_document_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                personnummer,
                uploaded_at,
                source_filename,
                detected_personnummer,
                printed_at,
                high_cost_period_end.isoformat() if high_cost_period_end else None,
                raw_document_text,
            ),
        )


def delete_prescription(personnummer: str, prescription_id: str) -> bool:
    init_db()
    with _connect() as connection:
        cursor = connection.execute(
            """
            DELETE FROM patient_prescriptions
            WHERE personnummer = ? AND prescription_id = ?
            """,
            (personnummer, prescription_id),
        )

        return cursor.rowcount > 0
