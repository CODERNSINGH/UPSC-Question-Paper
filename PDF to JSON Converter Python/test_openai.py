import os
import fitz  # PyMuPDF
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

# =====================================================
# CONFIG
# =====================================================
PDF_INPUT_DIR = "CSAT PDFs"
JSON_OUTPUT_DIR = "JSON_PAPERS"

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

# =====================================================
# SAFE JSON PARSER
# =====================================================
def parse_llm_json(raw_text: str):

    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    # Remove markdown fences if any
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

    chunks = []
    current = ""

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
# LLM CONVERTER — GPT-4.0-MINI
# =====================================================
def convert_chunk_to_json(chunk):

    prompt = f"""
You are an expert UPSC CSAT tutor and math parser.

This PDF text may contain BROKEN math
because superscripts/subscripts are lost.

------------------------------------------------
MATH RECOVERY RULES (CRITICAL):

If you see corrupted math such as:

x2, y3, a4, r2, t1
2pi r
√x
>= <=

You MUST reconstruct proper LaTeX.

Examples:

x2 + y2 = z2  →  $x^2 + y^2 = z^2$
a1 + a2       →  $a_1 + a_2$
2pi r         →  $2\\pi r$
√x            →  $\\sqrt{{x}}$

Use context and explanation to infer.

You are ALLOWED to fix broken math.
Do NOT keep corrupted forms.
------------------------------------------------

TASK:

Convert the text into structured JSON.
Improve explanations using LaTeX.

Rules:

- Preserve question meaning
- Preserve numbering
- Preserve correct answers
- Do NOT remove content
- You MAY fix math
- You MAY add helpful equations

------------------------------------
STRUCTURE:

Return ONLY JSON array.

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
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        return parse_llm_json(response.choices[0].message.content)

    except Exception as e:

        print("❌ OpenAI API error:", e)

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
