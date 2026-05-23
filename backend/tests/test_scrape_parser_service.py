from app.services.scrape_parser_service import ScrapeParserService


SAMPLE_SCRAPE = """Aktuella recept
Utskrivet: 2026-05-10 16:39
Agnes Viktoria Malmros, 20070515
Högkostnadsperiod t.o.m: 2026-05-24
Läkemedel
Verksamt ämne Förskrivet läkemedel Användning Är utfärdat av Senaste uttag Mängd som återstår
Atomoxetin Atomoxetin Actavis, kapsel,
hård 60 mg Teva Sweden
AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad:
Ja
1 kapsel till kvällen för
behandling av ADHD/ADD
Göran Heden,, Läkare
SLSO, Psykiatri Södra
Stockholm
Gustavsberg -2025-11-13
Atomoxetine STADA,
kapsel, hård 60 mg
2026-04-06
1 av 5 uttag kvar
30 kapsel/kapslar
Minsta tid mellan
uttag:
3 veckors intervall
Gäller t.o.m.: 2026-11-13
Melatonin Melatonin AGB, tablett 4
mg
1 x 100 tablett(er)
(Kan bytas)
Patient förmånsberättigad:
Ja
1 tablett till kvällen för bättre
sömn. Erhåller adhd diagnos.
Göran Heden,, Läkare
SLSO, Psykiatri Södra
Stockholm
Gustavsberg -2025-10-20
Melatonin OPQ Labs,
filmdragerad tablett 4
mg
2026-02-28
1 av 4 uttag kvar
100 tablett(er)
Nästa uttag inom
förmånen tidigast:
2025-12-29
Gäller t.o.m.: 2026-10-20
Drospirenon Slinda, filmdragerad tablett
4 mg
1 x 84 tablett(er)
(Kan bytas)
Patient förmånsberättigad:
Ja
1 tablett dagligen som
preventivmedel vid samma
tidpunkt varje dag.
Paula Björn,, Läkare
Considra AB
Nacka
073-745 72 36
2025-08-21
2026-03-28 1 av 4 uttag kvar
84 tablett(er)
Gäller t.o.m.: 2026-08-21
"""


def test_parse_scrape_extracts_prescriptions() -> None:
    parser = ScrapeParserService()

    result = parser.parse(SAMPLE_SCRAPE)

    assert result.personnummer == "20070515"
    assert result.printed_at == "2026-05-10 16:39"
    assert result.high_cost_period_end is not None
    assert "Aktuella recept" in result.raw_document_text
    assert len(result.prescriptions) == 3
    assert result.prescriptions[0].medication_name.startswith("Atomoxetin Actavis")
    assert result.prescriptions[0].administration_times == ["kväll"]
    assert result.prescriptions[0].raw_prescription_text is not None
    assert result.prescriptions[1].medication_name.startswith("Melatonin AGB")
    assert result.prescriptions[2].medication_name.startswith("Drospirenon Slinda")


def test_atomoxetin_parsing_consistency_with_varying_senaste_uttag() -> None:
    parser = ScrapeParserService()
    
    # Variant 1: "Ej uttaget" in Senaste uttag column - parses correctly
    variant_1 = """Aktuella recept
Agnes Viktoria Malmros, 20070515
Läkemedel
Verksamt ämne Förskrivet läkemedel Användning Är utfärdat av Senaste uttag Mängd som återstår
Atomoxetin Atomoxetin Actavis, kapsel,
hård 60 mg Teva Sweden
AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad:
Ja
1 kapsel till kvällen för
behandling av ADHD/ADD
Johan Dagh,, Läkare
SLSO, Psykiatri Södra
Stockholm
Nacka -2026-05-11
Ej uttaget 5 av 5 uttag kvar
150 kapsel/kapslar
Minsta tid mellan
uttag:
3 veckors intervall
Gäller t.o.m.: 2027-05-11
"""
    
    # Variant 2: "Atomoxetine STADA..." in Senaste uttag column - potentially causes confusion
    variant_2 = """Aktuella recept
Agnes Viktoria Malmros, 20070515
Läkemedel
Verksamt ämne Förskrivet läkemedel Användning Är utfärdat av Senaste uttag Mängd som återstår
Atomoxetin Atomoxetin Actavis, kapsel,
hård 60 mg Teva Sweden
AB
1 x 30 kapsel/kapslar
(Kan bytas)
Patient förmånsberättigad:
Ja
1 kapsel till kvällen för
behandling av ADHD/ADD
Göran Heden,, Läkare
SLSO, Psykiatri Södra
Stockholm
Gustavsberg -2025-11-13
Atomoxetine STADA,
kapsel, hård 60 mg
2026-04-06
1 av 5 uttag kvar
30 kapsel/kapslar
Minsta tid mellan
uttag:
3 veckors intervall
Gäller t.o.m.: 2026-11-13
"""

    result_1 = parser.parse(variant_1)
    result_2 = parser.parse(variant_2)

    assert len(result_1.prescriptions) == 1
    assert len(result_2.prescriptions) == 1
    
    # Both should parse to same medication despite different Senaste uttag content
    assert result_1.prescriptions[0].medication_name.startswith("Atomoxetin Actavis")
    assert result_2.prescriptions[0].medication_name.startswith("Atomoxetin Actavis")
    
    assert result_1.prescriptions[0].active_substance == "Atomoxetin"
    assert result_2.prescriptions[0].active_substance == "Atomoxetin"


def test_pdf_column_bleed_causes_duplicate_medication_in_block() -> None:
    """
    Reproduces the bug where PDF column "Senaste uttag" bleeds into medication block,
    causing two medications to be parsed as one with corrupted name.
    
    In the PDF from May 17, 2026:
    - First Atomoxetin: Senaste uttag = "Ej uttaget"
    - Second Atomoxetin: Senaste uttag = "Atomoxetine STADA, kapsel, hård 60 mg 2026-04-06"
    
    When text is extracted from the table format, the second prescription's
    "Senaste uttag" info can bleed into the first Atomoxetin block, causing
    `_extract_medication_name()` to pick up "Atomoxetine" instead of "Atomoxetin".
    """
    parser = ScrapeParserService()
    
    # Simulates what happens when "Senaste uttag" column content (with date) bleeds into next block
    # The first block ends with "Gäller t.o.m.: 2027-05-11" and should be separate,
    # but the second Atomoxetin's "Senaste uttag" ("Atomoxetine STADA..." + date) bleeds in
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

    result = parser.parse(corrupted_text)
    
    # Should parse as 2 separate Atomoxetin prescriptions
    assert len(result.prescriptions) == 2
    
    # Both should have clean medication names (no "STADA" or "Atomoxetine" from bleed)
    assert result.prescriptions[0].medication_name.startswith("Atomoxetin Actavis")
    assert result.prescriptions[1].medication_name.startswith("Atomoxetin Actavis")
    
    # Active substance should be "Atomoxetin" for both, not "Atomoxetine"
    assert result.prescriptions[0].active_substance == "Atomoxetin"
    assert result.prescriptions[1].active_substance == "Atomoxetin"
    
    # Prescribed products should not contain "STADA" from the other prescription
    assert "STADA" not in result.prescriptions[0].prescribed_product
    assert "STADA" not in result.prescriptions[1].prescribed_product


def test_parse_scrape_handles_split_lines_and_refills() -> None:
    parser = ScrapeParserService()
    sample = """Aktuella recept
Camilla Avagliano, 198001011234
Läkemedel
Escitalopram Escitalopram Accord,
filmdragerad tablett 20 mg
1 x 98 tablett(er)
(Kan bytas)
Patient förmånsberättigad:
Ja
1 tablett på morgonen För
humöret
Camilla Avagliano,,
Läkare
SLSO, Psykiatri Södra
Stockholm
Nacka -2026-05-15
Ej uttaget 2 av 2 uttag kvar
196 tablett(er)
Minsta tid mellan
uttag:
2 månaders intervall
Gäller t.o.m.: 2027-05-15
"""

    result = parser.parse(sample)

    assert len(result.prescriptions) == 1
    item = result.prescriptions[0]
    assert item.package_size == 98
    assert item.prescribed_daily_dose == 1.0
    assert item.dose_per_intake == 1.0
    assert item.refill_remaining == 2
    assert item.refill_total == 2
    assert item.remaining_packages == 2
    assert item.has_active_prescription is True
