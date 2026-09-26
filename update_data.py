"""
Refresh data/fuel_prices.csv from the Petroleum Planning & Analysis Cell (PPAC).

PPAC publishes a daily PDF containing the full retail selling price history
of petrol and diesel in the four metro cities since 16-Jun-2017. This script
finds the latest PDF on the PPAC page, parses every row and rewrites the CSV.

Usage:
    poetry run python update_data.py
"""

import csv
import io
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

PAGE_URL = (
    "https://ppac.gov.in/retail-selling-price-rsp-of-petrol-diesel-and-domestic-lpg/"
    "rsp-of-petrol-and-diesel-in-metro-cities-since-16-6-2017"
)
PDF_LINK_PATTERN = re.compile(r"https://ppac\.gov\.in/[^\"']*DailyPriceMSHSD_Metro[^\"']*\.pdf")
OUTPUT_PATH = Path(__file__).parent / "data" / "fuel_prices.csv"

CITIES = ["Delhi", "Mumbai", "Chennai", "Kolkata"]

# Each row: date, 4 petrol prices, date, 4 diesel prices (cities in CITIES order)
DATE = r"(\d{1,2}-[A-Za-z]{3}-\d{2})"
PRICES = r"\s+(\d+\.\d+)" * 4
ROW_PATTERN = re.compile(DATE + PRICES + r"\s+" + DATE + PRICES)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def find_pdf_url() -> str:
    html = fetch(PAGE_URL).decode("utf-8", errors="ignore")
    match = PDF_LINK_PATTERN.search(html)
    if not match:
        raise RuntimeError(f"Could not find the daily price PDF link on {PAGE_URL}")
    return match.group(0).replace(" ", "%20")


def parse_pdf(pdf_bytes: bytes) -> list[tuple[str, str, str, float]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    records = []
    for row in ROW_PATTERN.findall(text):
        if row[0] != row[5]:
            raise RuntimeError(f"Petrol and diesel dates differ in row: {row}")
        date = datetime.strptime(row[0], "%d-%b-%y").strftime("%Y-%m-%d")
        for i, city in enumerate(CITIES):
            records.append((date, city, "Petrol", float(row[1 + i])))
            records.append((date, city, "Diesel", float(row[6 + i])))
    return records


def count_existing_rows() -> int:
    if not OUTPUT_PATH.exists():
        return 0
    with OUTPUT_PATH.open() as f:
        return max(sum(1 for _ in f) - 1, 0)


def main() -> int:
    pdf_url = find_pdf_url()
    print(f"Downloading {pdf_url}")
    records = parse_pdf(fetch(pdf_url))

    # Guard against a changed PDF layout silently wiping the dataset
    existing = count_existing_rows()
    if len(records) < existing:
        print(
            f"Parsed {len(records)} rows, fewer than the {existing} already stored. "
            "Aborting without writing.",
            file=sys.stderr,
        )
        return 1

    records.sort()
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "City", "Product", "Price"])
        writer.writerows(records)

    print(
        f"Wrote {len(records)} rows ({records[0][0]} to {records[-1][0]}) "
        f"to {OUTPUT_PATH.relative_to(Path(__file__).parent)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
