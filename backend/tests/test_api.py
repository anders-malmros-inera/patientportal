from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


SCRAPE_UPLOAD = """Aktuella recept
Agnes Viktoria Malmros, 20070515
Läkemedel
Atomoxetin Atomoxetin Actavis, kapsel, hård 60 mg
1 x 30 kapsel/kapslar
1 kapsel till kvällen för behandling av ADHD/ADD
1 av 5 uttag kvar
Gäller t.o.m.: 2026-11-13
"""


def _login(personnummer: str) -> dict[str, str]:
    login_response = client.post("/api/auth/login", json={"personnummer": personnummer})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_scrape(headers: dict[str, str]) -> None:
    files = {"file": ("lakemedel.txt", SCRAPE_UPLOAD.encode("utf-8"), "text/plain")}
    upload_response = client.post("/api/prescriptions/upload-scrape", headers=headers, files=files)
    assert upload_response.status_code == 200


def test_login_and_fetch_renewal_advice() -> None:
    headers = _login("200705151234")
    _upload_scrape(headers)

    advice_response = client.get("/api/renewal-advice", headers=headers)

    assert advice_response.status_code == 200
    payload = advice_response.json()
    assert "advice" in payload
    assert len(payload["advice"]) > 0


def test_prescriptions_include_active_status() -> None:
    headers = _login("200705151234")
    _upload_scrape(headers)

    response = client.get("/api/prescriptions", headers=headers)

    assert response.status_code == 200
    prescriptions = response.json()
    assert len(prescriptions) > 0
    assert "has_active_prescription" in prescriptions[0]


def test_unauthorized_without_token() -> None:
    response = client.get("/api/prescriptions")
    assert response.status_code == 401


def test_upload_scrape_file() -> None:
    headers = _login("200705151234")
    files = {"file": ("lakemedel.txt", SCRAPE_UPLOAD.encode("utf-8"), "text/plain")}

    upload_response = client.post("/api/prescriptions/upload-scrape", headers=headers, files=files)

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["imported_prescriptions"] == 1
    assert payload["detected_personnummer"] == "20070515"


def test_delete_prescription() -> None:
    headers = _login("200705151234")
    _upload_scrape(headers)

    prescriptions_response = client.get("/api/prescriptions", headers=headers)
    assert prescriptions_response.status_code == 200
    prescriptions = prescriptions_response.json()
    assert len(prescriptions) > 0
    prescription_id = prescriptions[0]["id"]

    delete_response = client.delete(f"/api/prescriptions/{prescription_id}", headers=headers)
    assert delete_response.status_code == 204

    followup_response = client.get("/api/prescriptions", headers=headers)
    assert followup_response.status_code == 200
    remaining = followup_response.json()
    assert all(item["id"] != prescription_id for item in remaining)


def test_manual_medication_is_saved_without_active_prescription() -> None:
    headers = _login("200705151234")

    add_response = client.post(
        "/api/prescriptions/manual",
        headers=headers,
        json={"medication_name": "Ipren 200 mg"},
    )
    assert add_response.status_code == 200

    prescriptions_response = client.get("/api/prescriptions", headers=headers)
    assert prescriptions_response.status_code == 200
    prescriptions = prescriptions_response.json()
    manual_items = [item for item in prescriptions if item["medication_name"] == "Ipren 200 mg"]
    assert len(manual_items) == 1
    assert manual_items[0]["has_active_prescription"] is False
