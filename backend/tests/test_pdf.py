"""Test to debug PDF parsing with actual problematic PDF"""
import os
from app.services.scrape_parser_service import ScrapeParserService

# Get the PDF from the tests directory
pdf_path = os.path.join(os.path.dirname(__file__), "test_prescription.pdf")

if os.path.exists(pdf_path):
    parser = ScrapeParserService()
    result = parser.parse_pdf(pdf_path)
    
    print(f"\n=== PDF PARSING RESULTS ===")
    print(f"Total prescriptions found: {len(result.prescriptions)}")
    
    for i, rx in enumerate(result.prescriptions):
        print(f"\n--- Prescription {i+1} ---")
        print(f"Medication Name: {rx.medication_name}")
        print(f"Active Substance: {rx.active_substance}")
        print(f"Prescribed Product: {rx.prescribed_product}")
        print(f"Package Size: {rx.package_size}")
        print(f"Dose Per Intake: {rx.dose_per_intake}")
        print(f"Dose Unit: {rx.dose_unit}")
        print(f"Valid Until: {rx.valid_until}")
else:
    print(f"PDF not found at {pdf_path}")
