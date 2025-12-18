from docx import Document
from pathlib import Path
import sys

try:
    # Try multiple path approaches
    file_paths = [
        "Keys etc.docx",
        Path("Keys etc.docx"),
        Path.cwd() / "Keys etc.docx"
    ]
    
    doc = None
    for path in file_paths:
        try:
            doc = Document(str(path))
            print(f"Successfully opened: {path}")
            break
        except:
            continue
    
    if not doc:
        raise Exception("Could not open file with any path method")
    
    print("="*80)
    print("KEYS ETC.DOCX")
    print("="*80)
    print()
    for para in doc.paragraphs:
        if para.text.strip():
            print(para.text)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

