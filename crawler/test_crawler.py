"""Run offline: python -m unittest -v"""
import unittest
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from xml.etree import ElementTree as ET

from crawler import clean_xml_text, export_xlsx, normalize, parse_doctor, sitemap_locations, reparse


class CrawlerTests(unittest.TestCase):
    def test_sitemap_excludes_images(self):
        root = ET.fromstring('''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
        <url><loc>https://www.doctorbangladesh.com/dr-x/</loc>
        <image:image><image:loc>https://www.doctorbangladesh.com/photo.jpg</image:loc></image:image>
        </url></urlset>''')
        self.assertEqual(sitemap_locations(root), ["https://www.doctorbangladesh.com/dr-x/"])

    def test_profile_and_multiple_chambers(self):
        html = '''<div class="bc"><a>Doctors in Dhaka</a></div><article>
        <h1>Dr. Example</h1><ul class="doctor-info">
        <li>BMDC REG. NO: A-123</li><li title="Degree">MBBS<br>MD</li>
        <li title="Specialty">Cardiology</li></ul><div class="entry-content">
        <h2>Chamber & Appointment</h2><p><strong>Hospital One</strong>
        Address: Road 1<strong>Visiting Hour: 4pm (Closed: Friday)</strong>
        Appointment: +880123<a class="call-now" href="tel:+880123">Call Now</a></p>
        <p><strong>Hospital Two</strong>Address: Road 2<strong>Visiting Hour: Unknown</strong></p>
        <p>বাংলা biography</p><script>bad script</script></div></article>
        <div id="comments">Private review text</div>'''
        result = parse_doctor(html, "https://www.doctorbangladesh.com/dr-example/")
        self.assertEqual(result["qualifications"], "MBBS MD")
        self.assertEqual(result["bmdc_reg_no"], "A-123")
        self.assertEqual(result["region"], "Dhaka")
        self.assertEqual(len(result["chambers"]), 2)
        self.assertEqual(result["chambers"][0]["address"], "Road 1")
        self.assertEqual(result["chambers"][0]["appointment"], "+880123")
        self.assertEqual(result["chambers"][1]["visiting_hours"], "Unknown")
        self.assertIn("বাংলা", result["profile_text"])
        self.assertNotIn("bad script", result["profile_text"])
        self.assertNotIn("Private review", result["profile_text"])
        self.assertEqual(result["warnings"], [])

    def test_phone_and_cached_upgrade(self):
        html = '''<article><h1>Dr. Test</h1><ul class="doctor-info"></ul>
        <div class="entry-content"><p><strong>Hospital</strong>
        Address: Room No: 925, House 12, Rajshahi
        Visiting Hour: 5pm to 9pm Appointment: +880 1711-223344, 09612345678</p>
        <p><strong>Other Hospital</strong>Address: House 301, Dhaka
        Visiting Hour: Unknown</p></div></article>'''
        url = "https://www.doctorbangladesh.com/dr-test/"
        record = parse_doctor(html, url)
        self.assertNotIn("chamber_number", record["chambers"][0])
        self.assertEqual(record["chambers"][0]["phones"], ["+8801711223344", "09612345678"])
        self.assertIsNone(record["region"])
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE pages (url TEXT, html TEXT, record TEXT)")
            record["scraped_at"] = "original timestamp"
            record["chambers"][0]["chamber_number"] = "925"
            db.execute("INSERT INTO pages VALUES (?, ?, ?)", (url, html, json.dumps(record)))
            reparse(db)
            updated = json.loads(db.execute("SELECT record FROM pages").fetchone()[0])
            self.assertEqual(updated["scraped_at"], "original timestamp")
            self.assertNotIn("chamber_number", updated["chambers"][0])

    def test_non_profile_and_missing_fields(self):
        self.assertIsNone(parse_doctor("<article><h1>Doctors</h1></article>", "https://www.doctorbangladesh.com/"))
        record = parse_doctor('<article><h1>Dr. X</h1><ul class="doctor-info"></ul></article>', "https://www.doctorbangladesh.com/dr-x/")
        self.assertIsNone(record["bmdc_reg_no"])
        self.assertIn("Missing chambers", record["warnings"])

    def test_url_boundary(self):
        self.assertEqual(normalize("/dr-x/#reviews"), "https://www.doctorbangladesh.com/dr-x/")
        for url in ("https://evil.example/", "/?s=doctor", "file:///etc/passwd"):
            with self.assertRaises(ValueError):
                normalize(url)

    def test_export_xlsx_flattened_chambers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/doctors.xlsx"
            export_xlsx([{
                "name": "Dr. Example",
                "specialty": "Cardiology",
                "qualifications": "MBBS",
                "designation": None,
                "workplace": "Hospital",
                "experience": None,
                "bmdc_reg_no": "A-123",
                "region": "Dhaka",
                "source_url": "https://www.doctorbangladesh.com/dr-example/",
                "chambers": [{
                    "hospital": "Hospital One",
                    "address": "Road 1",
                    "phones": ["+880123"],
                    "visiting_hours": "4pm",
                }],
            }], Path(path))
            with zipfile.ZipFile(path) as archive:
                sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn("doctor_name", sheet)
            self.assertIn("Dr. Example", sheet)
            self.assertIn("+880123", sheet)

    def test_excel_text_removes_invalid_xml_controls(self):
        self.assertEqual(clean_xml_text("A\x00B\x08C\tD"), "ABC\tD")


if __name__ == "__main__":
    unittest.main()
