# import os
# import fitz  # PyMuPDF
# import json
# import re
# from openai import OpenAI

# import os
# import json

# PDF_INPUT_DIR = "CSAT PDFs"
# JSON_OUTPUT_DIR = "JSON_PAPERS"


# # let's Use the .env file to load environment variables
# from dotenv import load_dotenv
# load_dotenv()



# # ----------------------------
# # OPENAI CLIENT
# # ----------------------------
# client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

# # ----------------------------
# # SAFE JSON PARSER
# # ----------------------------
# def parse_llm_json(raw_text: str):
#     if not raw_text or not raw_text.strip():
#         return []

#     text = raw_text.strip()
#     text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
#     text = re.sub(r"^```\s*", "", text)
#     text = re.sub(r"\s*```$", "", text)

#     try:
#         data = json.loads(text)
#         return data if isinstance(data, list) else []
#     except json.JSONDecodeError as e:
#         print("JSON parse error:", e)
#         print("LLM output preview:\n", text[:300])
#         return []

# # ----------------------------
# # PDF TEXT EXTRACTION
# # ----------------------------
# def extract_pdf_text(pdf_path):
#     doc = fitz.open(pdf_path)
#     text = ""
#     for page in doc:
#         text += page.get_text("text") + "\n"
#     return text

# # ----------------------------
# # EXAM-AWARE CHUNKER
# # ----------------------------
# def exam_aware_chunker(text, max_chars=8000):
#     text = re.sub(r"\n{2,}", "\n", text)

#     lines = text.split("\n")
#     chunks, current = [], ""

#     for line in lines:
#         if len(current) + len(line) < max_chars:
#             current += line + "\n"
#         else:
#             chunks.append(current.strip())
#             current = line + "\n"

#     if current.strip():
#         chunks.append(current.strip())

#     return chunks

# # ----------------------------
# # LLM CONVERTER
# # ----------------------------
# def convert_chunk_to_json(chunk):
#     prompt = f"""
# You are an expert UPSC CSAT exam document parser.

# Convert the following text into structured JSON.

# Rules:
# - Do NOT summarize
# - Do NOT skip content
# - Maintain order
# - Return ONLY JSON array (no markdown)

# Each item:
# type: instruction | passage | question | text

# For question include:
# question_no
# question_text
# options
# correct_answer
# explanation

# TEXT:
# {chunk}
# """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0
#     )

#     return parse_llm_json(response.choices[0].message.content)

# # ----------------------------
# # MAIN FUNCTION (THIS WAS MISSING)
# # ----------------------------


# def main(pdf_path):
#     print("Processing:", pdf_path)

#     raw_text = extract_pdf_text(pdf_path)
#     print("Extracted characters:", len(raw_text))

#     chunks = exam_aware_chunker(raw_text)
#     print("Total chunks:", len(chunks))

#     all_content = []

#     for i, chunk in enumerate(chunks):
#         print(f"Processing chunk {i+1}/{len(chunks)}")
#         parsed = convert_chunk_to_json(chunk)
#         all_content.extend(parsed)

#     final_json = {
#         "source_file": os.path.basename(pdf_path),
#         "total_chunks": len(chunks),
#         "content": all_content
#     }

#     # 🔹 Output JSON path (same name as PDF)
#     output_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
#     output_path = os.path.join(JSON_OUTPUT_DIR, output_filename)

#     with open(output_path, "w") as f:
#         json.dump(final_json, f, indent=2)

#     print("JSON saved:", output_path)
#     print("TOTAL ITEMS:", len(all_content))


# # ----------------------------
# # BATCH PROCESS PDFs FROM CSAT PYQs
# # ----------------------------
# if __name__ == "__main__":
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     os.chdir(current_dir)

#     pdf_dir = os.path.join(current_dir, PDF_INPUT_DIR)

#     if not os.path.exists(pdf_dir):
#         raise FileNotFoundError(f"❌ PDF folder not found: {PDF_INPUT_DIR}")

#     # Ensure output folder exists
#     os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

#     pdfs = [
#         f for f in os.listdir(pdf_dir)
#         if f.lower().endswith(".pdf")
#     ]

#     if not pdfs:
#         raise FileNotFoundError("❌ No PDFs found in CSAT PYQs folder")

#     print(f"📂 Found {len(pdfs)} PDF(s) in {PDF_INPUT_DIR}")

#     for pdf in pdfs:
#         pdf_path = os.path.join(pdf_dir, pdf)

#         print("\n==============================")
#         print("📄 Using PDF:", pdf)
#         print("==============================")

#         try:
#             main(pdf_path)
#         except Exception as e:
#             print(f"❌ Failed processing {pdf}: {e}")






# # ----------------------------
# # New Feature From HERE (Passage Based Extraction)
# # ----------------------------


import os
import fitz  # PyMuPDF
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

# ============================
# CONFIG
# ============================
PDF_INPUT_DIR = "CSAT PDFs"
JSON_OUTPUT_DIR = "JSON_PAPERS"

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

# ============================
# SAFE JSON PARSER
# ============================
def parse_llm_json(raw_text: str):
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        print("JSON parse error:", e)
        print("LLM output preview:\n", text[:300])
        return []

# ============================
# PDF TEXT EXTRACTION
# ============================
def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# ============================
# EXAM-AWARE CHUNKER
# ============================
def exam_aware_chunker(text, max_chars=8000):
    text = re.sub(r"\n{2,}", "\n", text)

    lines = text.split("\n")
    chunks, current = [], ""

    for line in lines:
        if len(current) + len(line) < max_chars:
            current += line + "\n"
        else:
            chunks.append(current.strip())
            current = line + "\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks

# ============================
# LLM CONVERTER
# ============================
def convert_chunk_to_json(chunk):
    prompt = f"""
You are an expert UPSC CSAT exam document parser.

Convert the following text into structured JSON.

Rules:
- Do NOT summarize
- Do NOT skip content
- Maintain order
- Return ONLY JSON array (no markdown)

Each item:
type: instruction | passage | question | text

For question include:
question_no
question_text
options
correct_answer
explanation

TEXT:
{chunk}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return parse_llm_json(response.choices[0].message.content)

# =====================================================
# 🟢 NEW: GROUP QUESTIONS UNDER THEIR PASSAGES
# =====================================================
def group_questions_under_passages(items):
    grouped = []
    current_passage = None

    for item in items:
        item_type = item.get("type")

        if item_type == "passage":
            current_passage = {
                "type": "passage",
                "text": item.get("text"),
                "questions": []
            }
            grouped.append(current_passage)

        elif item_type == "question" and current_passage:
            current_passage["questions"].append(item)

        else:
            grouped.append(item)
            current_passage = None

    return grouped

# ============================
# MAIN FUNCTION
# ============================
def main(pdf_path):
    print("Processing:", pdf_path)

    raw_text = extract_pdf_text(pdf_path)
    print("Extracted characters:", len(raw_text))

    chunks = exam_aware_chunker(raw_text)
    print("Total chunks:", len(chunks))

    all_content = []

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        parsed = convert_chunk_to_json(chunk)
        all_content.extend(parsed)

    # 🟢 APPLY PASSAGE → QUESTION GROUPING
    structured_content = group_questions_under_passages(all_content)

    final_json = {
        "source_file": os.path.basename(pdf_path),
        "total_chunks": len(chunks),
        "content": structured_content
    }

    output_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
    output_path = os.path.join(JSON_OUTPUT_DIR, output_filename)

    with open(output_path, "w") as f:
        json.dump(final_json, f, indent=2)

    print("JSON saved:", output_path)
    print("TOTAL ITEMS:", len(structured_content))

# ============================
# BATCH PROCESS PDFs
# ============================
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)

    pdf_dir = os.path.join(current_dir, PDF_INPUT_DIR)
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(pdf_dir):
        raise FileNotFoundError(f"❌ PDF folder not found: {PDF_INPUT_DIR}")

    pdfs = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    if not pdfs:
        raise FileNotFoundError("❌ No PDFs found")

    print(f"📂 Found {len(pdfs)} PDF(s)")

    for pdf in pdfs:
        pdf_path = os.path.join(pdf_dir, pdf)
        print("\n==============================")
        print("📄 Using PDF:", pdf)
        print("==============================")

        try:
            main(pdf_path)
        except Exception as e:
            print(f"❌ Failed processing {pdf}: {e}")
