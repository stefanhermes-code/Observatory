"""
Add OPENAI_VECTOR_STORE_ID to .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load existing .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

vector_store_id = "vs_694227fc51288191a38ddee6dc957168"

# Read existing .env content
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
else:
    lines = []

# Check if OPENAI_VECTOR_STORE_ID already exists
has_vector_store = False
for i, line in enumerate(lines):
    if line.strip().startswith('OPENAI_VECTOR_STORE_ID'):
        # Update existing line
        lines[i] = f"OPENAI_VECTOR_STORE_ID={vector_store_id}\n"
        has_vector_store = True
        break

# Add if it doesn't exist
if not has_vector_store:
    # Add a blank line if file doesn't end with one
    if lines and not lines[-1].strip() == '':
        lines.append('\n')
    lines.append(f"OPENAI_VECTOR_STORE_ID={vector_store_id}\n")

# Write back to .env
with open(env_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"[SUCCESS] Added OPENAI_VECTOR_STORE_ID to .env file")
print(f"Vector Store ID: {vector_store_id}")
print("")
print("The upload script will now use this vector store.")

