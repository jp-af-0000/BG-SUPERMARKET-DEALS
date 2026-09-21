from datetime import datetime, timedelta
import io
import pandas as pd
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

# ------------------------------------------------------------------------------
# 1. LIDL (Direct Excel Export File)
# ------------------------------------------------------------------------------


def fetch_lidl_promos() -> pd.DataFrame:
    """Fetches Lidl daily promotional items directly from their official Excel export."""
    url = "https://www.lidl.bg/explore/assets/webPriceData/bg/ExportFirstList.xlsx"

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200 and len(res.content) > 100:
            print("[Lidl] Downloaded ExportFirstList.xlsx")
            excel_data = io.BytesIO(res.content)
            df = pd.read_excel(excel_data)

            # Map typical KZP Excel columns
            col_map = {
                "Наименование на артикула": "title",
                "Продукт": "title",
                "Промоционална цена": "price_promo",
                "Промо цена": "price_promo",
                "Предишна цена": "price_old",
                "Стара цена": "price_old",
                "Мярка": "unit",
                "EAN": "ean",
            }
            df = df.rename(columns=col_map)
            df["store"] = "Lidl"
            df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            return df
    except Exception as e:
        print(f"[Lidl] Excel fetch failed: {e}")

    print("[Lidl] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# 2. FANTASTICO (Direct KZP Compliance CSV)
# ------------------------------------------------------------------------------


def fetch_fantastico_promos() -> pd.DataFrame:
    """Fetches Fantastico daily promo CSV directly from public KZP endpoint."""
    for days_back in range(3):
        target_date = (datetime.now() - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )
        file_url = f"http://fantastico.bg/files/kzp/fantastico.csv?d={target_date}"

        try:
            res = requests.get(file_url, headers=HEADERS, timeout=10)
            if res.status_code == 200 and len(res.content) > 50:
                print(f"[Fantastico] Fetched CSV for {target_date}")
                csv_data = io.StringIO(res.text)
                df = pd.read_csv(csv_data, on_bad_lines="skip")

                col_map = {
                    "Продукт": "title",
                    "Наименование": "title",
                    "Промо цена": "price_promo",
                    "Стара цена": "price_old",
                    "Мярка": "unit",
                }
                df = df.rename(columns=col_map)
                df["store"] = "Fantastico"
                df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
                return df
        except Exception as e:
            print(f"[Fantastico] Failed for {target_date}: {e}")

    print("[Fantastico] 0 records fetched.")
    return pd.DataFrame()


# ------------------------------------------------------------------------------
# PIPELINE RUNNER
# ------------------------------------------------------------------------------


def run_pipeline():
    print("Starting Direct Data File Pipeline (Lidl + Fantastico)...\n")

    scrapers = [
        ("Lidl", fetch_lidl_promos),
        ("Fantastico", fetch_fantastico_promos),
    ]

    all_dfs = []

    for name, scraper_fn in scrapers:
        print(f"--- Fetching {name} ---")
        try:
            df = scraper_fn()
            if not df.empty:
                all_dfs.append(df)
                print(f"Result: {len(df)} items retrieved from {name}.\n")
            else:
                print(f"Result: 0 items returned for {name}.\n")
        except Exception as err:
            print(f"Error fetching {name}: {err}\n")

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
    else:
        print("Warning: No records extracted. Creating header-only CSV.")
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

    combined_df.to_csv("promos_v1.csv", index=False, encoding="utf-8")
    print(f"Pipeline finished. Saved {len(combined_df)} rows to promos_v1.csv")


if __name__ == "__main__":
    run_pipeline()
