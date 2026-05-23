import sys
import os
from pypdf import PdfReader
from app.services.scrape_parser_service import ScrapeParserService

def main():
    if len(sys.argv) < 2:
        print("Usage: py debug_parser.py path/to/pdf")
        return

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    # Extract text from PDF
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    # Parse using ScrapeParserService
    service = ScrapeParserService()
    result = service.parse(text)

    # Display results
    print(f"\n=== TOTAL PRESCRIPTIONS: {len(result.prescriptions)} ===\n")
    for i, p in enumerate(result.prescriptions, 1):
        print(f"--- Prescription {i} ---")
        print(f"Medication Name:    {p.medication_name}")
        print(f"Active Substance:   {p.active_substance}")
        print(f"Prescribed Product: {p.prescribed_product}")
        print(f"Prescribed Daily:   {p.prescribed_daily_dose}")
        print(f"Valid Until:        {p.valid_until}")
        print()

if __name__ == "__main__":
    main()
