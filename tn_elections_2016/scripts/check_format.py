import pdfplumber
import sys

def check_pdf(path):
    try:
        with pdfplumber.open(path) as pdf:
            text = pdf.pages[0].extract_text()
            if text:
                print(f"File: {path}")
                print("Text extracted successfully:")
                print(text[:500])
                return True
            else:
                print(f"File: {path}")
                print("No text extracted (likely image-based).")
                return False
    except Exception as e:
        print(f"Error checking {path}: {e}")
        return False

files = [
    "tn_elections_2016/raw_data/Ac036.pdf",
    "tn_elections_2016/raw_data/Ac037.pdf",
    "tn_elections_2016/raw_data/Ac029.pdf",
    "tn_elections_2016/raw_data/Ac028.pdf"
]

for f in files:
    check_pdf(f)
    print("-" * 40)
