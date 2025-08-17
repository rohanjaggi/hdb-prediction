import os, re
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from ingest import ensure_schema
from dotenv import load_dotenv

load_dotenv()

def engine():
    return create_engine(os.getenv("DATABASE_URL", "sqlite:///hdb.db"), future=True)

def median_storey(s: str | None) -> int | None:
    if not isinstance(s, str): return None
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        return (a + b) // 2
    return int(nums[0]) if nums else None

def remaining_lease_to_years(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return pd.NA

    # numeric handling
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, float):
        return int(round(x))

    #string handling
    s = str(x).strip().lower()
    if not s:
        return pd.NA

    y = re.search(r"(\d+)\s*(?:years)", s)
    if y:
        return int(y.group(1))
    if s.isdigit():
        return int(s)

    return pd.NA

def main():
    eng = engine()

    with eng.connect() as c:
        raw = pd.read_sql("SELECT * FROM transactions_raw", c)

    if raw.empty:
        print("transactions_raw empty")
        return

    df = raw.copy()

    df["storey_median"] = df["storey_range"].apply(median_storey)
    df["town_enc"] = df["town"].astype("category").cat.codes
    df["flat_type_enc"] = df["flat_type"].astype("category").cat.codes
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")
    df["year"] = df["month"].dt.year
    df["month_num"] = df["month"].dt.month
    df["remaining_lease_years"] = df["remaining_lease"].apply(remaining_lease_to_years)

    clean = pd.DataFrame({
        "id": range(len(df)),
        "month": df["month"],
        "year": df["year"],
        "month_num": df["month_num"],
        "town": df["town"],
        "town_enc": df["town_enc"],
        "flat_type": df["flat_type"],
        "flat_type_enc": df["flat_type_enc"],
        "block": df["block"],
        "street_name": df["street_name"],
        "storey_range": df["storey_range"],
        "storey_median": df["storey_median"],
        "floor_area_sqm": df["floor_area_sqm"],
        "flat_model": df["flat_model"],
        "lease_commence_date": df["lease_commence_date"],
        "remaining_lease": df["remaining_lease_years"],
        "resale_price": df["resale_price"],
        "_resource_id": df["_resource_id"],
        "_ingested_at": df["_ingested_at"]
    })

    with eng.begin() as c:
        ensure_schema(c)
        c.execute(text("DELETE FROM transactions_clean"))
        clean.to_sql("transactions_clean", c, if_exists="append", index=False)

    print(f"transactions_clean rows: {len(clean):,}")

if __name__ == "__main__":
    main()