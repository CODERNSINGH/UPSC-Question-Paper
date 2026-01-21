import json
import re
from firecrawl import FirecrawlApp

# API_KEY = "fc-8274191bede74cfe96809faddebb297b"
TARGET_URL = "https://www.visionias.in/resources/upsc-paper-solution/"

CSAT_PATTERNS = [
    r"paper[_\-]?2",
    r"csat"
]

def fetch_pdfs():
    app = FirecrawlApp(api_key=API_KEY)

    result = app.scrape_url(
        TARGET_URL,
        params={
            "formats": ["links"],
            "waitFor": 6000,
            "onlyMainContent": False
        }
    )

    links = result.get("links", [])
    print(f"Total links found: {len(links)}")

    pdfs = [
        link for link in links
        if link.endswith(".pdf") and "visionias" in link
    ]

    print(f"PDFs found: {len(pdfs)}")

    csat_pdfs = [
        link for link in pdfs
        if any(re.search(p, link.lower()) for p in CSAT_PATTERNS)
    ]

    csat_pdfs = sorted(set(csat_pdfs))
    return csat_pdfs


if __name__ == "__main__":
    csat_links = fetch_pdfs()

    with open("visionias_csat_pdfs.json", "w") as f:
        json.dump(csat_links, f, indent=2)

    print(f"✅ Saved {len(csat_links)} CSAT PDFs")
