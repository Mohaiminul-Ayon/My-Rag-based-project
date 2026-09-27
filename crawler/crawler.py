"""Doctor Bangladesh -> resumable SQLite cache + UTF-8 JSONL dataset."""
import argparse
import hashlib
import json
import re
import sqlite3
import time
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

BASE = "https://www.doctorbangladesh.com/"
AGENT = "DoctorDatasetLearningBot"
XLSX_COLUMNS = (
    "doctor_name",
    "specialty",
    "qualifications",
    "designation",
    "workplace",
    "experience",
    "bmdc_reg_no",
    "region",
    "hospital",
    "address",
    "phone",
    "visiting_hours",
    "source_url",
)


def normalize(url):
    parts = urlsplit(urljoin(BASE, url))
    if parts.scheme not in {"http", "https"} or parts.hostname not in {
        "www.doctorbangladesh.com", "doctorbangladesh.com"
    } or parts.port not in {None, 80, 443}:
        raise ValueError(f"Off-site URL rejected: {url}")
    if parts.query:
        raise ValueError(f"Query URL rejected: {url}")
    return urlunsplit(("https", "www.doctorbangladesh.com", parts.path or "/", "", ""))


def text(node):
    return node.get_text(" ", strip=True) if node else None


def parse_doctor(html, url):
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article")
    if not article or not article.select_one(".doctor-info"):
        return None
    name = text(article.select_one("h1"))
    if not name:
        raise ValueError("Doctor information found without a name")
    fields = {
        item.get("title", "").lower(): text(item)
        for item in article.select(".doctor-info li[title]")
    }
    info = text(article.select_one(".doctor-info")) or ""
    bmdc = re.search(r"BMDC\s*REG\.?\s*NO\s*:\s*([A-Za-z0-9-]+)", info, re.I)
    content = article.select_one(".entry-content")
    chambers = []
    if content:
        for paragraph in content.find_all("p"):
            raw = text(paragraph) or ""
            if "Address:" not in raw:
                continue
            def field(label):
                match = re.search(
                    rf"{label}\s*:\s*(.*?)(?=\s*(?:Address|Visiting Hours?|Appointment|Consultation Fee|Call Now)\s*:|\s*Call Now|$)",
                    raw, re.I,
                )
                return match.group(1).strip() if match else None
            address = field("Address")
            appointment = field("Appointment")
            phone_values = [
                a["href"][4:].strip() for a in paragraph.select('a[href^="tel:"]')
            ]
            if not phone_values:
                phone_values = re.findall(r"\+?\d[\d ()-]{4,}\d", appointment or "")
            phones = list(dict.fromkeys(
                re.sub(r"[\s()-]", "", value) for value in phone_values
            ))
            chambers.append({
                "hospital": raw.split("Address:", 1)[0].strip() or None,
                "address": address,
                "visiting_hours": field("Visiting Hours?"),
                "appointment": appointment,
                "phones": phones,
            })
        for unwanted in content.select("script, style, .adsense, ins, form, .call-now"):
            unwanted.decompose()
    updated = article.select_one(".doctor-editorial-note time[datetime]")
    breadcrumbs = [text(a) for a in soup.select(".bc a")]
    record = {
        "doctor_id": urlsplit(url).path.strip("/"),
        "name": name,
        "bmdc_reg_no": bmdc.group(1) if bmdc else None,
        "qualifications": fields.get("degree"),
        "specialty": fields.get("specialty"),
        "designation": fields.get("designation"),
        "workplace": fields.get("workplace"),
        "experience": fields.get("experiences") or fields.get("experience"),
        "region": next((value.removeprefix("Doctors in ") for value in breadcrumbs
                        if value and value.startswith("Doctors in ")), None),
        "breadcrumbs": breadcrumbs,
        "chambers": chambers,
        "profile_text": text(content),
        "source_url": url,
        "source_updated_at": updated["datetime"] if updated else None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": hashlib.sha256(html.encode("utf-8")).hexdigest(),
    }
    record["warnings"] = [
        f"Missing {key}" for key in ("qualifications", "specialty", "chambers")
        if not record[key]
    ]
    return record


def reparse(db):
    """Upgrade saved records from cached HTML without changing fetch timestamps."""
    for url, html, payload in db.execute(
        "SELECT url, html, record FROM pages WHERE record IS NOT NULL AND html IS NOT NULL"
    ).fetchall():
        previous = json.loads(payload)
        record = parse_doctor(html, previous["source_url"])
        if record is None:
            raise ValueError(f"Cached profile no longer parses: {url}")
        record["scraped_at"] = previous["scraped_at"]
        db.execute("UPDATE pages SET record=? WHERE url=?", (json.dumps(record, ensure_ascii=False), url))
    db.commit()


def xlsx_cell(column, row, value, style):
    if value is None:
        return f'<c r="{column}{row}" s="{style}"/>'
    return (
        f'<c r="{column}{row}" s="{style}" t="inlineStr"><is><t>{escape(clean_xml_text(value))}</t></is></c>'
    )


def clean_xml_text(value):
    return "".join(
        char for char in str(value)
        if char in "\t\n\r"
        or 0x20 <= ord(char) <= 0xD7FF
        or 0xE000 <= ord(char) <= 0xFFFD
        or 0x10000 <= ord(char) <= 0x10FFFF
    )


def xlsx_column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def export_xlsx(records, path):
    rows = [XLSX_COLUMNS]
    for record in records:
        chambers = record["chambers"] or [{}]
        for chamber in chambers:
            rows.append((
                record.get("name"),
                record.get("specialty"),
                record.get("qualifications"),
                record.get("designation"),
                record.get("workplace"),
                record.get("experience"),
                record.get("bmdc_reg_no"),
                record.get("region"),
                chamber.get("hospital"),
                chamber.get("address"),
                ", ".join(chamber.get("phones") or []),
                chamber.get("visiting_hours"),
                record.get("source_url"),
            ))
    sheet_rows = []
    for row_number, values in enumerate(rows, 1):
        style = 1 if row_number == 1 else 2 + (row_number % 2)
        cells = "".join(
            xlsx_cell(xlsx_column_name(index), row_number, value, style)
            for index, value in enumerate(values, 1)
        )
        height = ' ht="26" customHeight="1"' if row_number == 1 else ""
        sheet_rows.append(f'<row r="{row_number}"{height}>{cells}</row>')
    widths = (24, 22, 28, 28, 28, 20, 14, 14, 28, 42, 20, 24, 45)
    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, 1)
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><sheetFormatPr defaultRowHeight="18"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/></sheetView></sheetViews>'
        f'<cols>{columns}</cols><sheetData>'
        + "".join(sheet_rows)
        + '</sheetData><autoFilter ref="A1:M1"/></worksheet>'
    )
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Doctors" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sheet,
        "xl/styles.xml": styles,
    }
    temporary = path.with_suffix(".xlsx.tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    temporary.replace(path)


class Fetcher:
    def __init__(self, delay):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"{AGENT}/1.0 (educational dataset crawler)"
        self.delay = delay
        self.last_request = 0
        self.robots = None
        response = self.get(BASE + "robots.txt")
        self.robots = RobotFileParser()
        if response.status_code == 404:
            self.robots.parse([])
        else:
            response.raise_for_status()
            if "<html" in response.text.lower():
                raise ValueError("robots.txt returned HTML; cannot verify crawl rules")
            self.robots.parse(response.text.splitlines())
        self.delay = max(delay, self.robots.crawl_delay(AGENT) or 0)
        rate = self.robots.request_rate(AGENT)
        if rate:
            self.delay = max(self.delay, rate.seconds / rate.requests)

    def get(self, url):
        url = normalize(url)
        for redirect in range(6):
            if self.robots and not self.robots.can_fetch(AGENT, url):
                raise PermissionError(f"robots.txt disallows {url}")
            for attempt in range(3):
                time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
                self.last_request = time.monotonic()
                try:
                    response = self.session.get(url, timeout=30, allow_redirects=False)
                except requests.RequestException:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** (attempt + 1))
                    continue
                if response.status_code == 429:
                    raise RuntimeError("Server rate limit (429); stopped. Resume later with a larger --delay.")
                if response.status_code == 403:
                    raise RuntimeError("Server denied access (403); stopped without bypassing it.")
                if response.status_code >= 500 and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break
            if response.is_redirect:
                url = normalize(urljoin(url, response.headers["Location"]))
                continue
            response.encoding = "utf-8"
            return response
        raise ValueError("Too many redirects")


def sitemap_locations(root):
    # Only sitemap/url children, never nested image:loc entries.
    return [normalize(node.text.strip()) for node in root.findall("./{*}*/{*}loc") if node.text]


def discover(fetcher):
    pending = list(fetcher.robots.site_maps() or [BASE + "sitemap.xml"])
    visited, pages = set(), set()
    while pending:
        url = normalize(pending.pop(0))
        if url in visited:
            continue
        visited.add(url)
        response = fetcher.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        locations = sitemap_locations(root)
        if root.tag.endswith("sitemapindex"):
            pending.extend(locations)
        elif root.tag.endswith("urlset"):
            pages.update(locations)
        else:
            raise ValueError(f"Unexpected sitemap format: {url}")
        print(f"Sitemap: {url} ({len(pages)} URLs discovered)", flush=True)
    if not pages:
        raise ValueError("No URLs discovered; refusing to report an empty crawl as complete")
    return sorted(pages)


def export(db, directory):
    destination = directory / "doctors.jsonl"
    spreadsheet = directory / "doctors.xlsx"
    temporary = destination.with_suffix(".jsonl.tmp")
    records, warnings, count = [], 0, 0
    with temporary.open("w", encoding="utf-8") as output:
        for (payload,) in db.execute("SELECT record FROM pages WHERE record IS NOT NULL ORDER BY url"):
            output.write(payload + "\n")
            record = json.loads(payload)
            records.append(record)
            warnings += bool(record["warnings"])
            count += 1
    temporary.replace(destination)
    export_xlsx(records, spreadsheet)
    statuses = dict(db.execute("SELECT status, count(*) FROM pages GROUP BY status"))
    print(json.dumps({"doctors": count, "records_with_warnings": warnings, "pages": statuses}, indent=2))
    print(f"Dataset: {destination.resolve()}")
    print(f"Excel: {spreadsheet.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="Maximum pages this run; 0 = all pending pages")
    parser.add_argument("--delay", type=float, default=2, help="Minimum seconds between requests (at least 1)")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--url", help="Fetch one profile instead of discovering the sitemap")
    parser.add_argument("--rediscover", action="store_true", help="Refresh the sitemap URL list")
    parser.add_argument("--export-only", action="store_true", help="Export cached records without network access")
    parser.add_argument("--reparse", action="store_true", help="Reparse cached doctor HTML and export without network access")
    args = parser.parse_args()
    if args.limit < 0 or args.delay < 1:
        parser.error("--limit must be >= 0 and --delay must be >= 1")
    args.output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.output / "crawl.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending', html TEXT, record TEXT, error TEXT)")
        try:
            if args.reparse:
                reparse(db)
                return
            if args.export_only:
                return
            fetcher = Fetcher(args.delay)
            if args.url:
                urls = [normalize(args.url)]
            elif args.rediscover or not db.execute("SELECT 1 FROM pages LIMIT 1").fetchone():
                urls = discover(fetcher)
            else:
                urls = []
            db.executemany("INSERT OR IGNORE INTO pages(url) VALUES (?)", [(url,) for url in urls])
            db.commit()
            if args.url:
                pending = [(normalize(args.url),)]
            else:
                # Prioritize common doctor slugs, but inspect ALL sitemap URLs for coverage.
                pending = db.execute("SELECT url FROM pages WHERE status IN ('pending','error') ORDER BY CASE WHEN url LIKE '%/dr-%' OR url LIKE '%/prof-%' THEN 0 ELSE 1 END, url").fetchall()
            for (url,) in pending[:args.limit or None]:
                print(f"Fetching: {url}", flush=True)
                try:
                    response = fetcher.get(url)
                    response.raise_for_status()
                    record = parse_doctor(response.text, response.url)
                    if record is None and re.search(r"/(?:dr|prof)-", url):
                        raise ValueError("Expected doctor profile markup missing; inspect page before retry")
                    db.execute("UPDATE pages SET status=?, html=?, record=?, error=NULL WHERE url=?", (
                        "doctor" if record else "other", response.text,
                        json.dumps(record, ensure_ascii=False) if record else None, url,
                    ))
                except (requests.RequestException, ValueError, PermissionError) as exc:
                    db.execute("UPDATE pages SET status='error', error=? WHERE url=?", (str(exc), url))
                    print(f"Error: {exc}", flush=True)
                db.commit()
        except KeyboardInterrupt:
            print("Stopped; committed pages are saved. Run again to resume.")
        finally:
            export(db, args.output)


if __name__ == "__main__":
    main()
