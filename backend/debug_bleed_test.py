"""Debug the PDF column bleed test data"""
from app.services.scrape_parser_service import ScrapeParserService

corrupted_text = """Aktuella recept
Läkemedel

Verksamt ämne
Atomoxetin

Förskrivet läkemedel
Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)

Användning
1 kapsel till kvällen för behandling av ADHD/ADD

Är utfärdat av
Johan Dagh,, Läkare SLSO, Psykiatri Södra Stockholm Nacka
2026-05-11

Senaste uttag
Ej uttaget

Mängd som återstår
5 av 5 uttag kvar 150 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2027-05-11

Atomoxetine STADA, kapsel, hård 60 mg 2026-04-06

Verksamt ämne
Atomoxetin

Förskrivet läkemedel
Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)

Användning
1 kapsel till kvällen för behandling av ADHD/ADD

Är utfärdat av
Göran Heden,, Läkare SLSO, Psykiatri Södra Stockholm Gustavsberg
2025-11-13

Senaste uttag
Atomoxetine STADA, kapsel, hård 60 mg 2026-04-06

Mängd som återstår
1 av 5 uttag kvar 30 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2026-11-13
"""

parser = ScrapeParserService()
result = parser.parse(corrupted_text)

print(f"\nTotal prescriptions: {len(result.prescriptions)}\n")
for i, rx in enumerate(result.prescriptions):
    print(f"--- Prescription {i+1} ---")
    print(f"Medication Name:    {rx.medication_name}")
    print(f"Active Substance:   {rx.active_substance}")
    print(f"Prescribed Product: {rx.prescribed_product}")
    print(f"Valid Until:        {rx.valid_until}")
    print()
