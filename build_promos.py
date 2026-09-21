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


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
  df.columns = [str(c).strip() for c in df.columns]
  return df


# ------------------------------------------------------------------------------
# 1. LIDL (Retain All Columns, Filter Store 197)
# ------------------------------------------------------------------------------
def fetch_lidl_promos() -> pd.DataFrame:
  url = "https://www.lidl.bg/explore/assets/webPriceData/bg/ExportFirstList.xlsx"
  try:
    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code == 200 and len(res.content) > 100:
      df = pd.read_excel(io.BytesIO(res.content))
      df = clean_columns(df)

      store_col = next(
          (
              c
              for c in df.columns
              if "търговски" in c.lower() and "обект" in c.lower()
          ),
          None,
      )
      if store_col:
        df = df[
            df[store_col]
            .astype(str)
            .str.contains(LIDL_TARGET_STORE, na=False)
        ]

      df["store"] = "Lidl"
      df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
      print(f"[Lidl] Filtered rows: {len(df)}, columns: {len(df.columns)}")
      return df
  except Exception as e:
    print(f"[Lidl] Error: {e}")

  return pd.DataFrame()


# ------------------------------------------------------------------------------
# 2. FANTASTICO (Retain All Columns, Filter Store Ф12)
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
        df = pd.read_csv(io.StringIO(res.text), on_bad_lines="skip")
        df = clean_columns(df)

        store_col = next(
            (
                c
                for c in df.columns
                if "търговски" in c.lower() and "обект" in c.lower()
            ),
            None,
        )
        if store_col:
          df = df[
              df[store_col]
              .astype(str)
              .str.contains(FANTASTICO_TARGET_STORE, na=False)
          ]

        df["store"] = "Fantastico"
        df["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        print(
            "[Fantastico] Filtered rows:"
            f" {len(df)}, columns: {len(df.columns)}"
        )
        return df
    except Exception as e:
      print(f"[Fantastico] Error for {target_date}: {e}")

  return pd.DataFrame()


# ------------------------------------------------------------------------------
# PIPELINE RUNNER
# ------------------------------------------------------------------------------
def run_pipeline():
  print("Starting Full-Data Single-Store Pipeline...\n")
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
    except Exception as err:
      print(f"Error executing {name}: {err}")

  if all_dfs:
    # Concatenate union of all raw columns across both files
    combined_df = pd.concat(all_dfs, ignore_index=True, sort=False)
  else:
    combined_df = pd.DataFrame()

  combined_df.to_csv("promos_v1.csv", index=False, encoding="utf-8")
  print(
      f"\nPipeline finished. Total rows saved: {len(combined_df)} across"
      f" {len(combined_df.columns)} columns."
  )


if __name__ == "__main__":
  run_pipeline()
