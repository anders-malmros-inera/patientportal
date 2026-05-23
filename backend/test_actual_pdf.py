"""Test with actual PDF text from the May 17, 2026 prescription"""
from app.services.scrape_parser_service import ScrapeParserService

# This is how the PDF text appears from OCR - without explicit "Verksamt ämne:" labels
# The tables are flattened to text, so column headers and content mix
pdf_text = """Aktuella recept
Utskrivet: 2026-05-17 14:05
Agnes Viktoria Malmros, 20070515
Högkostnadsperiod t.o.m: 2026-05-24

Läkemedel
Verksamt ämne Förskrivet läkemedel Användning Är utfärdat av Senaste uttag Mängd som återstår

Escitalopram Escitalopram Accord, filmdragerad tablett 20 mg
1 x 98 tablett(er)
(Kan bytas)
Patient förmånsberättigad: Ja
1 tablett på morgonen För humöret
Camilla Avagliano,, Läkare SLSO, Psykiatri Södra Stockholm Nacka - 2026-05-15
Ej uttaget
2 av 2 uttag kvar 196 tablett(er)
Minsta tid mellan uttag: 2 månaders intervall
Gäller t.o.m.: 2027-05-15

Atomoxetin Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
1 kapsel till kvällen för behandling av ADHD/ADD
Johan Dagh,, Läkare SLSO, Psykiatri Södra Stockholm Nacka - 2026-05-11
Ej uttaget
5 av 5 uttag kvar 150 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2027-05-11

Atomoxetin Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
1 kapsel till kvällen för behandling av ADHD/ADD
Göran Heden,, Läkare SLSO, Psykiatri Södra Stockholm Gustavsberg - 2025-11-13
Atomoxetine STADA, kapsel, hård 60 mg 2026-04-06
1 av 5 uttag kvar 30 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2026-11-13

Melatonin Melatonin AGB, tablett 4 mg
1 x 100 tablett(er)
(Kan bytas)
Patient förmånsberättigad: Ja
1 tablett till kvällen för bättre sömn. Erhåller adhd diagnos.
Göran Heden,, Läkare SLSO, Psykiatri Södra Stockholm Gustavsberg - 2025-10-20
Melatonin OPQ Labs, filmdragerad tablett 4 mg 2026-02-28
1 av 4 uttag kvar 100 tablett(er)
Nästa uttag inom förmånen tidigast: 2025-12-29
Gäller t.o.m.: 2026-10-20
"""

service = ScrapeParserService()
result = service.parse(pdf_text)

print(f"\n=== PARSING RESULTS ===")
print(f"Total prescriptions: {len(result.prescriptions)}\n")

for i, rx in enumerate(result.prescriptions, 1):
    print(f"--- Prescription {i} ---")
    print(f"Active Substance:   {rx.active_substance}")
    print(f"Medication Name:    {rx.medication_name}")
    print(f"Prescribed Product: {rx.prescribed_product}")
    print(f"Valid Until:        {rx.valid_until}")
    print()
