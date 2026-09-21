from datetime import datetime, timedelta
import json
import re
import pandas as pd
import requests

# ------------------------------------------------------------------------------
# Output Schema standard across all scrapers:
# ['store', 'title', 'price_promo', 'price_old', 'unit', 'ean', 'updated_at']
# ------------------------------------------------------------------------------


def fetch_hit_max_promos() -> pd.DataFrame:
    """Fetches Hit Max weekly promotional CSV directly from their public daily uploads."""
    base_url = "https://www.hit-max.bg/wp-content/uploads/Prices/000000000/"

    for days_back in range(2):
        target_date = (datetime.now() - timedelta(days=days_back)).strftime(
            "%Y%m%d"
        )
        file_name = f"PRM_000000000_{target_date}.csv"
        file_url = f"{base_url}{file_name}"

        try:
            res = requests.head(file_url, timeout=5)
            if res.status_code == 200:
                df = pd.read_csv(file_url, encoding="utf-8", on_bad_lines="skip")
                # Standardize schema (adjust column mappings as per exact CSV headers)
                df["store"] = "Hit Max"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
        except Exception as e:
            print(f"[Hit Max] Error fetching {file_url}: {e}")

    print("[Hit Max] No file found for today or yesterday.")
    return pd.DataFrame()


def fetch_billa_promos(city_code: str = "68134") -> pd.DataFrame:
    """Fetches daily Billa catalog data directly from Billa Service System JSON backend.

    Default city_code 68134 = Sofia.
    """
    url = f"https://euro.b-ss.eu/data.php?city={city_code}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

        if not data:
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
    # Example using Lidl's web offer / promotional payload structure
    url = f"https://www.lidl.bg/p/api/gridboxes/{country_code}/bg"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)
            df["store"] = "Lidl"
            df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            return df
    except Exception as e:
        print(f"[Lidl] Error fetching data: {e}")

    return pd.DataFrame()


def fetch_fantastico_promos() -> pd.DataFrame:
    """Fetches promotional offers from Fantastico."""
    url = "https://www.fantastico.bg/special-offers"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            # Parse HTML / embedded data logic
            df = pd.DataFrame()  # Replace with specific HTML parsing logic
            df["store"] = "Fantastico"
            df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            return df
    except Exception as e:
        print(f"[Fantastico] Error fetching data: {e}")

    return pd.DataFrame()


def run_pipeline():
    """Main aggregation runner for GitHub Actions."""
    print("Starting V1 Supermarket Promo Extraction pipeline...")

    scrapers = [
        ("Hit Max", fetch_hit_max_promos),
        ("Billa", fetch_billa_promos),
        ("Lidl", fetch_lidl_promos),
        ("Fantastico", fetch_fantastico_promos),
    ]

    all_dfs = []

    for name, scraper_fn in scrapers:
        print(f"Fetching {name}...")
        df = scraper_fn()
        if not df.empty:
            all_dfs.append(df)
            print(f"  -> {len(df)} items retrieved from {name}.")
        else:
            print(f"  -> No data returned for {name}.")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.to_csv("promos_v1.csv", index=False, encoding="utf-8")
        print(
            f"\nPipeline finished. Total items saved to promos_v1.csv: {len(combined_df)}"
        )
    else:
        print("\nPipeline completed with no records extracted.")


if __name__ == "__main__":
    run_pipeline()
