from datetime import datetime, timedelta
import json
import re
from bs4 import BeautifulSoup
import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
}

# ------------------------------------------------------------------------------
# 1. HIT MAX SCRAPER
# ------------------------------------------------------------------------------


def fetch_hit_max_promos() -> pd.DataFrame:
    """Fetches Hit Max daily promotional CSV files."""
    base_url = "https://www.hit-max.bg/wp-content/uploads/Prices/000000000/"

    # Look back up to 5 days to handle weekends or delayed uploads
    for days_back in range(5):
        target_date = (datetime.now() - timedelta(days=days_back)).strftime(
            "%Y%m%d"
        )
        file_name = f"PRM_000000000_{target_date}.csv"
        file_url = f"{base_url}{file_name}"

        try:
            res = requests.get(file_url, headers=HEADERS, timeout=10)
            if res.status_code == 200 and len(res.content) > 100:
                print(f"[Hit Max] Successfully downloaded {file_name}")
                df = pd.read_csv(file_url, encoding="utf-8", on_bad_lines="skip")

                # Normalize common Hit Max CSV column names
                rename_map = {
                    "Наименование": "title",
                    "Промо цена": "price_promo",
                    "Редовна цена": "price_old",
                    "Мярка": "unit",
                    "EAN": "ean",
                }
                df = df.rename(columns=rename_map)
                df["store"] = "Hit Max"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
        except Exception as e:
            print(f"[Hit Max] Failed attempt for {target_date}: {e}")

    print("[Hit Max] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# 2. BILLA SCRAPER
# ------------------------------------------------------------------------------


def fetch_billa_promos(city_code: str = "68134") -> pd.DataFrame:
    """Fetches active promo items from Billa Service System backend (Sofia = 68134)."""
    url = f"https://euro.b-ss.eu/data.php?city={city_code}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list):
                df = pd.DataFrame(data)

                # Normalize keys if JSON returns standard field names
                col_map = {
                    "name": "title",
                    "price": "price_promo",
                    "old_price": "price_old",
                }
                df = df.rename(columns=col_map)
                df["store"] = "Billa"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
    except Exception as e:
        print(f"[Billa] Error fetching data: {e}")

    print("[Billa] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# 3. LIDL SCRAPER
# ------------------------------------------------------------------------------


def fetch_lidl_promos() -> pd.DataFrame:
    """Scrapes Lidl Bulgaria active weekly promotional offers."""
    url = "https://www.lidl.bg/c/promocii/a1000"

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            items = []

            # Find product grid cards
            grid_items = soup.find_all(
                "article", class_=re.compile("product|grid-box")
            ) or soup.find_all("div", class_=re.compile("product"))

            for card in grid_items:
                title_elem = card.find(
                    ["h2", "h3", "strong"], class_=re.compile("title|heading")
                )
                price_elem = card.find(
                    "span", class_=re.compile("price|current")
                )

                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True)

                    items.append(
                        {
                            "store": "Lidl",
                            "title": title,
                            "price_promo": price,
                            "price_old": None,
                            "unit": None,
                            "ean": None,
                            "updated_at": datetime.now().strftime("%Y-%m-%d"),
                        }
                    )

            if items:
                return pd.DataFrame(items)

    except Exception as e:
        print(f"[Lidl] Scraper error: {e}")

    print("[Lidl] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# 4. FANTASTICO SCRAPER
# ------------------------------------------------------------------------------


def fetch_fantastico_promos() -> pd.DataFrame:
    """Scrapes promo offers from Fantastico's public promotions page."""
    url = "https://www.fantastico.bg/promotions"

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            items = []

            # Extract promo product cards
            cards = soup.find_all(
                "div", class_=re.compile("product|promo|item")
            )

            for card in cards:
                title_elem = card.find(["div", "span", "p"], class_="title")
                price_elem = card.find(["div", "span"], class_="price")

                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True)

                    items.append(
                        {
                            "store": "Fantastico",
                            "title": title,
                            "price_promo": price,
                            "price_old": None,
                            "unit": None,
                            "ean": None,
                            "updated_at": datetime.now().strftime("%Y-%m-%d"),
                        }
                    )

            if items:
                return pd.DataFrame(items)

    except Exception as e:
        print(f"[Fantastico] Scraper error: {e}")

    print("[Fantastico] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# PIPELINE RUNNER
# ------------------------------------------------------------------------------


def run_pipeline():
    print("Starting V1 Supermarket Promo Extraction pipeline...\n")

    scrapers = [
        ("Hit Max", fetch_hit_max_promos),
        ("Billa", fetch_billa_promos),
        ("Lidl", fetch_lidl_promos),
        ("Fantastico", fetch_fantastico_promos),
    ]

    all_dfs = []

    for name, scraper_fn in scrapers:
        print(f"--- Fetching {name} ---")
        df = scraper_fn()
        if not df.empty:
            all_dfs.append(df)
            print(f"Result: {len(df)} items retrieved from {name}.\n")
        else:
            print(f"Result: 0 items returned for {name}.\n")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
    else:
        print("Warning: No records extracted. Creating schema-only CSV.")
        combined_df = pd.DataFrame(
            columns=[
                "store",
                "title",
                "price_promo",
                "price_old",
                "unit",
                "ean",
                "updated_at",
            ]
        )

    # Force write CSV output
    combined_df.to_csv("promos_v1.csv", index=False, encoding="utf-8")
    print(f"Pipeline finished. Total rows written to promos_v1.csv: {len(combined_df)}")


if __name__ == "__main__":
    run_pipeline()
