"""Extract raw text from PDF file to understand the actual format"""
import sys
from pathlib import Path

# Check if we can import pypdf
try:
    from pypdf import PdfReader
    print("pypdf imported successfully")
    
    # Look for PDF file in current directory or tests
    pdf_paths = [
        "test_prescription.pdf",
        "prescription.pdf",
        "../tests/test_prescription.pdf",
        "c:/dev/workspace/patientportal/backend/tests/test_prescription.pdf"
    ]
    
    pdf_found = None
    for path in pdf_paths:
        if Path(path).exists():
            pdf_found = path
            break
    
    if not pdf_found:
        print("PDF file not found. Looking for PDFs in workspace...")
        import os
        for root, dirs, files in os.walk("c:/dev/workspace"):
            for file in files:
                if file.endswith(".pdf"):
                    print(f"Found: {os.path.join(root, file)}")
                    if "prescription" in file.lower() or "recept" in file.lower():
                        pdf_found = os.path.join(root, file)
                        break
            if pdf_found:
                break
    
    if pdf_found:
        print(f"\nReading PDF: {pdf_found}")
        reader = PdfReader(pdf_found)
        print(f"Pages: {len(reader.pages)}")
        
        for page_num, page in enumerate(reader.pages):
            print(f"\n{'='*60}")
            print(f"PAGE {page_num + 1}")
            print(f"{'='*60}")
            text = page.extract_text()
            print(text)
            print(f"{'='*60}\n")
    else:
        print("No PDF files found")
        
except ImportError:
    print("pypdf not installed")
except Exception as e:
    print(f"Error: {e}")
