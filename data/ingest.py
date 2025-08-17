import os, time, argparse, requests, pandas as pd
from datetime import datetime, UTC
from sqlalchemy import create_engine, text

CKAN = "https://data.gov.sg/api/action/datastore_search"
RIDS = [
    "d_ea9ed51da2787afaf8e51f827c304208",  # 2015–2016
    "d_8b84c4ee58e3cfc0ece0d773c8ca6abc",  # 2017–present
]

KEEP = [
    "month","town","flat_type","block","street_name","storey_range",
    "floor_area_sqm","flat_model","lease_commence_date","remaining_lease","resale_price"
]

def engine():
    return create_engine(os.getenv("DATABASE_URL","sqlite:///hdb.db"), future=True)

def ensure_schema(conn):
    with open("db/schema.sql","r",encoding="utf-8") as f:
        for stmt in [s.strip() for s in f.read().split(";") if s.strip()]:
            conn.execute(text(stmt))

def stream_resource(rid, eng, limit):
    sess, offset, written = requests.Session(), 0, 0
    while True:
        r = sess.get(CKAN, params={"resource_id":rid,"limit":limit,"offset":offset}, timeout=90)
        r.raise_for_status()
        recs = r.json()["result"]["records"]
        if not recs: break   # stop when there r no more records

        page = pd.DataFrame.from_records(recs)
        for col in KEEP:
            if col not in page.columns:
                page[col] = None
        page = page[KEEP]
        page["_resource_id"], page["_ingested_at"] = rid, datetime.now(UTC)

        if not page.empty:
            page.to_sql("transactions_raw", eng, if_exists="append", index=False,
                        chunksize=2000, method="multi")
            written += len(page)

        offset += limit
        time.sleep(0.1)
    return written

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()

    eng = engine()
    with eng.begin() as c: 
        ensure_schema(c)
        for rid in RIDS:
            c.execute(text("DELETE FROM transactions_raw WHERE _resource_id = :rid"), {"rid": rid})

    total = sum(stream_resource(rid, eng, args.limit) for rid in RIDS)
    print(f"Rows ingested: {total:,}")

if __name__ == "__main__":
    main()