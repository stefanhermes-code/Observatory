from docx import Document
import sys

files = [
    "OpenAI Instructions.docx",
    "Generator Execution Pattern – Polyurethane Observatory.docx"
]

for filename in files:
    try:
        print(f"\n{'='*80}")
        print(f"FILE: {filename}")
        print(f"{'='*80}\n")
        doc = Document(filename)
        for para in doc.paragraphs:
            if para.text.strip():
                print(para.text)
        print("\n")
    except Exception as e:
        print(f"Error reading {filename}: {e}")

