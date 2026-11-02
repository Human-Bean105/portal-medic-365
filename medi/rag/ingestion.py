"""Downloads the two reference sources and turns them into documents with their original metadata.

Nothing here is invented: titles, URLs, groups, and dates come from the source files. The MedlinePlus snapshot date is
the "date-generated" stamp in the official XML download; guideline summaries carry no date of their own."""
import base64
import html
import io
import json
import re
import urllib.request
import zipfile
from xml.etree import ElementTree

MEDLINEPLUS_PAGE = "https://medlineplus.gov/xml.html"
GUIDELINES_URL = ("https://api.github.com/repos/bshepp/clinical-decision-support-agent/contents/"
                  "src/backend/app/data/clinical_guidelines.json")
MEDLINEPLUS_LABEL = "MedlinePlus (U.S. National Library of Medicine)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Medi-RAG-builder (Portal Medic 365 student project)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def html_to_text(fragment):
    """Plain text with one paragraph or list item per line; headings become lines starting with "## "."""
    text = re.sub(r"<h\d[^>]*>", "\n## ", fragment)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"</(p|ul|ol|h\d|li)>|<br\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip())


def medlineplus_documents():
    page = fetch(MEDLINEPLUS_PAGE).decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]*mplus_topics_compressed_[\d-]+\.zip)"', page)), reverse=True)
    if not links:
        raise SystemExit("Couldn't find the MedlinePlus download link.")
    url = links[0] if links[0].startswith("http") else "https://medlineplus.gov/" + links[0].lstrip("/")
    archive = zipfile.ZipFile(io.BytesIO(fetch(url)))
    root = ElementTree.fromstring(archive.read(archive.namelist()[0]))
    snapshot = root.get("date-generated")
    docs = []
    for topic in root.iter("health-topic"):
        summary = topic.findtext("full-summary") or ""
        if topic.get("language") != "English" or not summary.strip():
            continue
        docs.append({
            "doc_id": f"mlp-{topic.get('id')}",
            "type": "health_topic",
            "source": MEDLINEPLUS_LABEL,
            "title": topic.get("title"),
            "url": topic.get("url"),
            "language": "en",
            "groups": [g.text for g in topic.findall("group") if g.text],
            "also_called": [a.text for a in topic.findall("also-called") if a.text],
            "date_created": topic.get("date-created"),
            "snapshot_date": snapshot,
            "text": html_to_text(summary),
        })
    return docs, {"medlineplus_download": url, "medlineplus_date_generated": snapshot}


def guideline_documents():
    docs = []
    for g in json.loads(base64.b64decode(json.loads(fetch(GUIDELINES_URL))["content"])):
        docs.append({
            "doc_id": f"gl-{g['id']}",
            "type": "guideline_summary",
            "source": f"{g['source']} (summary)",
            "title": g["title"],
            "url": g.get("url", ""),
            "language": "en",
            "groups": [g["specialty"]] if g.get("specialty") else [],
            "also_called": [],
            "date_created": None,
            "snapshot_date": None,
            "text": g["text"].strip(),
        })
    return docs, {"guidelines_source": GUIDELINES_URL}
