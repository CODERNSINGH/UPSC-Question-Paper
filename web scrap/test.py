import os
import fitz  # PyMuPDF
import json
import re
from openai import OpenAI


# let's Use the .env file to load environment variables
from dotenv import load_dotenv
load_dotenv()



# ----------------------------
# OPENAI CLIENT
# ----------------------------
client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

# ----------------------------
# SAFE JSON PARSER
# ----------------------------
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
        print("❌ JSON parse error:", e)
        print("LLM output preview:\n", text[:300])
        return []

# ----------------------------
# PDF TEXT EXTRACTION
# ----------------------------
def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# ----------------------------
# EXAM-AWARE CHUNKER
# ----------------------------
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

# ----------------------------
# LLM CONVERTER
# ----------------------------
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

# ----------------------------
# MAIN FUNCTION (THIS WAS MISSING)
# ----------------------------
def main(pdf_path):
    print("📄 Processing:", pdf_path)

    raw_text = extract_pdf_text(pdf_path)
    print("Extracted characters:", len(raw_text))

    chunks = exam_aware_chunker(raw_text)
    print("Total chunks:", len(chunks))

    all_content = []

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        parsed = convert_chunk_to_json(chunk)
        all_content.extend(parsed)

    final_json = {
        "source_file": os.path.basename(pdf_path),
        "total_chunks": len(chunks),
        "content": all_content
    }

    with open("FULL_PDF_STRUCTURED_OUTPUT.json", "w") as f:
        json.dump(final_json, f, indent=2)

    print("✅ JSON saved: FULL_PDF_STRUCTURED_OUTPUT.json")
    print("TOTAL ITEMS:", len(all_content))

# ----------------------------
# AUTO-FETCH PDF FROM SAME FOLDER
# ----------------------------
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdfs = [f for f in os.listdir(current_dir) if f.lower().endswith(".pdf")]

    if not pdfs:
        raise FileNotFoundError("❌ No PDF found in current folder")

    if len(pdfs) > 1:
        raise ValueError(f"❌ Multiple PDFs found: {pdfs}")

    pdf_path = os.path.join(current_dir, pdfs[0])
    print("📄 Using PDF:", pdf_path)

    main(pdf_path)
