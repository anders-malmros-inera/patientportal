from app.services.scrape_parser_service import ScrapeParserService
import json

# Use the exact string from debug_blocks.py
pdf_text = """Aktuella recept
Utskrivet: 2026-05-17 14:05
Agnes Viktoria Malmros, 20070515
Högkostnadsperiod t.o.m: 2026-05-24

Läkemedel
Verksamt ämne Förskrivet läkemedel Användning Är utfärdat av Senaste uttag
 Mängd som återstår

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
"""

service = ScrapeParserService()
blocks = service._split_medication_blocks(pdf_text)

print(f"Total blocks found: {len(blocks)}")
for i, block in enumerate(blocks, 1):
    result = service._parse_block(block, i, None, None)
    if not result:
        print(f"Block {i} failed to parse.")
        continue
    if i in [2, 3]:
        print(f"=== Block {i} ===")
        print(f"active_substance: {result.active_substance}")
        print(f"medication_name: {result.medication_name}")
        print(f"prescribed_product: {result.prescribed_product}")
        print(f"dose: {result.dose_per_intake}")
        print(f"administration_times: {result.administration_times}")
        print(f"instruction_text: {result.instruction_text}")
        print()
