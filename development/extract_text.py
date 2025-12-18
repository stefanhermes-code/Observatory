import os
import sys
from pathlib import Path
import json

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

PDF_LIB = None
try:
    import PyPDF2
    HAS_PDF = True
    PDF_LIB = 'PyPDF2'
except ImportError:
    try:
        import pdfplumber
        HAS_PDF = True
        PDF_LIB = 'pdfplumber'
    except ImportError:
        HAS_PDF = False

def extract_docx_text(file_path):
    """Extract text from a .docx file"""
    if not HAS_DOCX:
        return None
    try:
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        return f"Error reading docx: {e}"

def extract_pdf_text(file_path):
    """Extract text from a PDF file"""
    if not HAS_PDF:
        return None
    try:
        if PDF_LIB == 'pdfplumber':
            import pdfplumber
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or '')
            return '\n'.join(text)
        else:
            text = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
    except Exception as e:
        return f"Error reading PDF: {e}"

def main():
    folder = Path('.')
    results = {}
    
    for file_path in sorted(folder.iterdir()):
        if file_path.suffix.lower() == '.docx':
            print(f"Extracting from {file_path.name}...", file=sys.stderr)
            text = extract_docx_text(file_path)
            if text:
                results[file_path.name] = text
        elif file_path.suffix.lower() == '.pdf':
            print(f"Extracting from {file_path.name}...", file=sys.stderr)
            text = extract_pdf_text(file_path)
            if text:
                results[file_path.name] = text
    
    # Output results as JSON-like structure
    sys.stdout.reconfigure(encoding='utf-8')
    for filename, content in results.items():
        print(f"\n{'='*80}")
        print(f"FILE: {filename}")
        print(f"{'='*80}")
        if content:
            try:
                print(content)
            except UnicodeEncodeError:
                print(content.encode('utf-8', errors='replace').decode('utf-8'))
        print()

if __name__ == '__main__':
    main()

