"""Debug script to test parsing with actual PDF text from the formatted table"""
from app.services.scrape_parser_service import ScrapeParserService

# Text extracted from the properly formatted table sections of the PDF
pdf_text = """Aktuella recept
Utskrivet: 2026-05-17 14:05
Agnes Viktoria Malmros, 20070515
Högkostnadsperiod t.o.m: 2026-05-24

Läkemedel
Verksamt ämne: Escitalopram
Förskrivet läkemedel: Escitalopram Accord, filmdragerad tablett 20 mg
1 x 98 tablett(er)
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 tablett på morgonen För humöret
Är utfärdat av: Camilla Avagliano,, Läkare SLSO, Psykiatri Södra Stockholm Nacka -
2026-05-15
Senaste uttag: Ej uttaget
Mängd som återstår: 2 av 2 uttag kvar 196 tablett(er)
Minsta tid mellan uttag: 2 månaders intervall
Gäller t.o.m.: 2027-05-15

Verksamt ämne: Alimemazin
Förskrivet läkemedel: Alimemazin Evolan, kapsel, hård 20 mg
1 x 1 x 100 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 kapsel på eftermiddagen, 1 kapsel till kvällen, 1 kapsel till natten samt 1 kap vid behov mot ångest.
Är utfärdat av: Johan Dagh,, Läkare SLSO, Psykiatri Södra Stockholm Nacka -
2026-05-11
Senaste uttag: Ej uttaget
Mängd som återstår: 2 av 2 uttag kvar 200 kapsel/kapslar
Minsta tid mellan uttag: 1 månad
Gäller t.o.m.: 2027-05-11

Verksamt ämne: Lisdexamfetamin
Förskrivet läkemedel: Elvanse, kapsel, hård 70 mg Takeda Pharma AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 kapsel på morgonen för behandling av ADHD
Är utfärdat av: Johan Dagh,, Läkare SLSO, Psykiatri Södra Stockholm Nacka -
2026-05-11
Senaste uttag: Ej uttaget
Mängd som återstår: 4 av 4 uttag kvar 120 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2027-05-11

Verksamt ämne: Atomoxetin
Förskrivet läkemedel: Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 kapsel till kvällen för behandling av ADHD/ADD
Är utfärdat av: Johan Dagh,, Läkare SLSO, Psykiatri Södra Stockholm Nacka -
2026-05-11
Senaste uttag: Ej uttaget
Mängd som återstår: 5 av 5 uttag kvar 150 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2027-05-11

Verksamt ämne: Atomoxetin
Förskrivet läkemedel: Atomoxetin Actavis, kapsel, hård 60 mg Teva Sweden AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 kapsel till kvällen för behandling av ADHD/ADD
Är utfärdat av: Göran Heden,, Läkare SLSO, Psykiatri Södra Stockholm Gustavsberg -
2025-11-13
Senaste uttag: Atomoxetine STADA, kapsel, hård 60 mg 2026-04-06
Mängd som återstår: 1 av 5 uttag kvar 30 kapsel/kapslar
Minsta tid mellan uttag: 3 veckors intervall
Gäller t.o.m.: 2026-11-13

Verksamt ämne: Melatonin
Förskrivet läkemedel: Melatonin AGB, tablett 4 mg
1 x 100 tablett(er)
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 tablett till kvällen för bättre sömn. Erhäller adhd diagnos.
Är utfärdat av: Göran Heden,, Läkare SLSO, Psykiatri Södra Stockholm Gustavsberg -
2025-10-20
Senaste uttag: Melatonin OPQ Labs, filmdragerad tablett 4 mg 2026-02-28
Mängd som återstår: 1 av 4 uttag kvar 100 tablett(er)
Nästa uttag inom förmånen tidigast: 2025-12-29
Gäller t.o.m.: 2026-10-20

Verksamt ämne: Drospirenon
Förskrivet läkemedel: Slinda, filmdragerad tablett 4 mg
1 x 84 tablett(er)
(Kan bytas)
Patient förmånsberättigad: Ja
Användning: 1 tablett dagligen som preventivmedel vid samma tidpunkt varje dag. För statabletten tas den första blödningsdagen i den naturliga menscykeln.
Är utfärdat av: Paula Björn,, Läkare Considra AB Nacka 073-745 72 36 -
2025-08-21
Senaste uttag: 2026-03-28
Mängd som återstår: 1 av 4 uttag kvar 84 tablett(er)
Gäller t.o.m.: 2026-08-21
"""

service = ScrapeParserService()
result = service.parse(pdf_text)

print(f"\n=== PDF PARSING RESULTS ===")
print(f"Total prescriptions found: {len(result.prescriptions)}\n")

for i, rx in enumerate(result.prescriptions, 1):
    print(f"--- Prescription {i} ---")
    print(f"Medication Name:      {rx.medication_name}")
    print(f"Active Substance:     {rx.active_substance}")
    print(f"Prescribed Product:   {rx.prescribed_product}")
    print(f"Package Size:         {rx.package_size}")
    print(f"Prescribed Daily:     {rx.prescribed_daily_dose}")
    print(f"Dose Per Intake:      {rx.dose_per_intake}")
    print(f"Dose Unit:            {rx.dose_unit}")
    print(f"Valid Until:          {rx.valid_until}")
    print()

