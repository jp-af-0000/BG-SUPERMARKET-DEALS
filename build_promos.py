from datetime import datetime, timedelta
import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_hit_max_promos() -> pd.DataFrame:
    """Fetches Hit Max weekly promotional CSV directly from their public daily uploads."""
    base_url = "https://www.hit-max.bg/wp-content/uploads/Prices/000000000/"

    # Search past 3 days in case of weekend/holiday delay
    for days_back in range(3):
        target_date = (datetime.now() - timedelta(days=days_back)).strftime(
            "%Y%m%d"
        )
        file_name = f"PRM_000000000_{target_date}.csv"
        file_url = f"{base_url}{file_name}"

        try:
            res = requests.get(file_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                print(f"[Hit Max] Found valid CSV at {file_name}")
                df = pd.read_csv(file_url, encoding="utf-8", on_bad_lines="skip")
                df["store"] = "Hit Max"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
            else:
                print(
                    f"[Hit Max] {file_name} returned status code {res.status_code}"
                )
        except Exception as e:
            print(f"[Hit Max] Error fetching {file_name}: {e}")

    print("[Hit Max] No valid file found for the last 3 days.")
    return pd.DataFrame()


def fetch_billa_promos(city_code: str = "68134") -> pd.DataFrame:
    """Fetches daily Billa catalog data directly from Billa Service System JSON backend."""
    url = f"https://euro.b-ss.eu/data.php?city={city_code}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[Billa] Request status code: {res.status_code}")
        res.raise_for_status()

        data = res.json()
        if not data:
            print("[Billa] Returned empty JSON payload.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["store"] = "Billa"
        df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        return df
    except Exception as e:
        print(f"[Billa] Error fetching data: {e}")
        return pd.DataFrame()


def fetch_lidl_promos(country_code: str = "bg") -> pd.DataFrame:
    """Fetches active promotional offer items for Lidl Bulgaria."""
    url = f"https://www.lidl.bg/p/api/gridboxes/{country_code}/bg"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[Lidl] Request status code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df["store"] = "Lidl"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
    except Exception as e:
        print(f"[Lidl] Error fetching data: {e}")

    return pd.DataFrame()


def fetch_fantastico_promos() -> pd.DataFrame:
    """Placeholder for Fantastico parser."""
    df = pd.DataFrame()
    return df


def run_pipeline():
    """Main aggregation runner for GitHub Actions."""
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

    # Always construct a DataFrame and output promos_v1.csv
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
    else:
        print("Warning: No data collected from any store. Writing header-only CSV.")
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

    # Force saving the CSV file so Git always finds it
    combined_df.to_csv("promos_v1.csv", index=False, encoding="utf-8")
    print(f"Pipeline finished. Saved {len(combined_df)} rows to promos_v1.csv")


if __name__ == "__main__":
    run_pipeline()
