from datetime import datetime
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

LIDL_TARGET_STORE = "197"
FANTASTICO_TARGET_STORE = "Ф12"


# ------------------------------------------------------------------------------
# 1. LIDL (Filtered)
# ------------------------------------------------------------------------------
def fetch_lidl_promos() -> pd.DataFrame:
  url = "https://www.lidl.bg/explore/assets/webPriceData/bg/ExportFirstList.xlsx"
  try:
    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code == 200 and len(res.content) > 100:
      excel_data = io.BytesIO(res.content)
      df = pd.read_excel(excel_data)

      col_map = {
          "Търговски обект": "store_location",
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

      if "store_location" in df.columns:
        df = df[
            df["store_location"]
            .astype(str)
            .str.contains(LIDL_TARGET_STORE, na=False)
        ]

      df["store"] = "Lidl"
      df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
      return df
  except Exception as e:
    print(f"[Lidl] Error: {e}")

  return pd.DataFrame()


# ------------------------------------------------------------------------------
# 2. FANTASTICO (Filtered)
# ------------------------------------------------------------------------------
def fetch_fantastico_promos() -> pd.DataFrame:
  for days_back in range(3):
    target_date = (
        datetime.now() - pd.Timedelta(days=days_back)
    ).strftime("%Y-%m-%d")
    file_url = f"http://fantastico.bg/files/kzp/fantastico.csv?d={target_date}"
    try:
      res = requests.get(file_url, headers=HEADERS, timeout=10)
      if res.status_code == 200 and len(res.content) > 50:
        csv_data = io.StringIO(res.text)
        df = pd.read_csv(csv_data, on_bad_lines="skip")

        col_map = {
            "Търговски обект": "store_location",
            "Продукт": "title",
            "Наименование": "title",
            "Промо цена": "price_promo",
            "Стара цена": "price_old",
            "Мярка": "unit",
            "EAN": "ean",
        }
        df = df.rename(columns=col_map)

        if "store_location" in df.columns:
          df = df[
              df["store_location"]
              .astype(str)
              .str.contains(FANTASTICO_TARGET_STORE, na=False)
          ]

        df["store"] = "Fantastico"
        df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        return df
    except Exception as e:
      print(f"[Fantastico] Error for {target_date}: {e}")

  return pd.DataFrame()


# ------------------------------------------------------------------------------
# PIPELINE RUNNER
# ------------------------------------------------------------------------------
def run_pipeline():
  print("Starting Single-Store Promo Pipeline...\n")
  scrapers = [
      ("Lidl", fetch_lidl_promos),
      ("Fantastico", fetch_fantastico_promos),
  ]

  all_dfs = []
  for name, scraper_fn in scrapers:
    try:
      df = scraper_fn()
      if not df.empty:
        all_dfs.append(df)
        print(f"Result: {len(df)} items retrieved for {name}.")
      else:
        print(f"Result: 0 items returned for {name}.")
    except Exception as err:
      print(f"Error executing {name}: {err}")

  if all_dfs:
    combined_df = pd.concat(all_dfs, ignore_index=True)
    desired_cols = [
        "store",
        "title",
        "price_promo",
        "price_old",
        "unit",
        "ean",
        "updated_at",
    ]
    existing_cols = [c for c in desired_cols if c in combined_df.columns]
    combined_df = combined_df[existing_cols]

    dup_cols = [
        c for c in ["store", "title", "price_promo"] if c in combined_df.columns
    ]
    if dup_cols:
      combined_df = combined_df.drop_duplicates(subset=dup_cols)
  else:
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
  print(f"\nPipeline finished. Saved {len(combined_df)} rows to promos_v1.csv")


if __name__ == "__main__":
  run_pipeline()
