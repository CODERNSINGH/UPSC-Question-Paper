import os
import fitz  # PyMuPDF
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai

# =====================================================
# CONFIG
# =====================================================
PDF_INPUT_DIR = "CSAT PDFs"
JSON_OUTPUT_DIR = "JSON_PAPERS"

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro")

# =====================================================
# SAFE JSON PARSER
# =====================================================
def parse_llm_json(raw_text: str):
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    # Remove markdown fences safely
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        print("❌ JSON parse error:", e)
        print("🔍 LLM output preview:\n", text[:400])
        return []

# =====================================================
# PDF TEXT EXTRACTION
# =====================================================
def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text("text") + "\n"

    return text

# =====================================================
# EXAM-AWARE CHUNKER
# =====================================================
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

# =====================================================
# LLM CONVERTER (GEMINI PRO + MATH SAFE)
# =====================================================
def convert_chunk_to_json(chunk):

    prompt = f"""
You are an expert UPSC CSAT exam document parser.

IMPORTANT CONTEXT:
- This is a PREVIOUS YEAR QUESTION (PYQ).
- Mathematical expressions in PYQs are ALWAYS correct.
- Your job is to STRUCTURE and NORMALIZE, not to invent.

CRITICAL MATH RULES:

1. Convert raw math into LaTeX if needed:
   - x2 → x^2
   - y3 → y^3
   - x/y → \\frac{{x}}{{y}}
   - √x → \\sqrt{{x}}
   - >= → \\ge
   - <= → \\le

2. Wrap math in:
   - Inline: $...$
   - Block: $$...$$ (only if needed)

3. If already LaTeX → DO NOT CHANGE.

4. NEVER change meaning.
5. NEVER invent equations.
6. NEVER modify answers.
7. ONLY normalize formatting.

------------------------------------
STRUCTURE RULES:

- Do NOT summarize
- Do NOT skip content
- Maintain order
- Return ONLY JSON array
- NO markdown
- NO comments

Each item:
type: instruction | passage | question | text

For question include:
question_no
question_text
options
correct_answer
explanation

------------------------------------
TEXT:
{chunk}

Return ONLY valid JSON.
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "max_output_tokens": 8192
            }
        )

        return parse_llm_json(response.text)

    except Exception as e:
        print("❌ Gemini API failed:", e)
        return []

# =====================================================
# GROUP QUESTIONS UNDER PASSAGES
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

# =====================================================
# MAIN PROCESSOR
# =====================================================
def main(pdf_path):

    print("📄 Processing:", pdf_path)

    raw_text = extract_pdf_text(pdf_path)
    print("🔢 Extracted characters:", len(raw_text))

    chunks = exam_aware_chunker(raw_text)
    print("🧩 Total chunks:", len(chunks))

    all_content = []

    for i, chunk in enumerate(chunks):

        print(f"➡️ Processing chunk {i+1}/{len(chunks)}")

        parsed = convert_chunk_to_json(chunk)

        all_content.extend(parsed)

    structured_content = group_questions_under_passages(all_content)

    final_json = {
        "source_file": os.path.basename(pdf_path),
        "total_chunks": len(chunks),
        "content": structured_content
    }

    output_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"

    output_path = os.path.join(JSON_OUTPUT_DIR, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    print("✅ JSON saved:", output_path)
    print("📦 TOTAL ITEMS:", len(structured_content))

# =====================================================
# BATCH RUNNER
# =====================================================
if __name__ == "__main__":

    base_dir = os.path.dirname(os.path.abspath(__file__))

    os.chdir(base_dir)

    pdf_dir = os.path.join(base_dir, PDF_INPUT_DIR)

    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(pdf_dir):
        raise FileNotFoundError(f"❌ PDF folder not found: {PDF_INPUT_DIR}")

    pdfs = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    if not pdfs:
        raise FileNotFoundError("❌ No PDFs found")

    print(f"📂 Found {len(pdfs)} PDF(s)")

    for pdf in pdfs:

        print("\n==============================")
        print("📄 Using PDF:", pdf)
        print("==============================")

        try:
            main(os.path.join(pdf_dir, pdf))

        except Exception as e:
            print(f"❌ Failed processing {pdf}: {e}")
