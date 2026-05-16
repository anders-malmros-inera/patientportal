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
    assert result.prescriptions[0].administration_times == ["kvall"]
    assert result.prescriptions[0].raw_prescription_text is not None
    assert result.prescriptions[1].medication_name.startswith("Melatonin AGB")
    assert result.prescriptions[2].medication_name.startswith("Drospirenon Slinda")
