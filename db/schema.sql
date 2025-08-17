-- Raw
CREATE TABLE IF NOT EXISTS transactions_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  month TEXT NOT NULL,
  town TEXT,
  flat_type TEXT,
  block TEXT,
  street_name TEXT,
  storey_range TEXT,
  floor_area_sqm REAL,
  flat_model TEXT,
  lease_commence_date INTEGER,
  remaining_lease TEXT,
  resale_price REAL,
  _resource_id TEXT,
  _ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- clean
CREATE TABLE IF NOT EXISTS transactions_clean (
  id INTEGER PRIMARY KEY,
  month DATE NOT NULL,
  year INTEGER,
  quarter TEXT,
  town TEXT,
  flat_type TEXT,
  block TEXT,
  street_name TEXT,
  storey_range TEXT,
  storey_median INTEGER,
  floor_area_sqm REAL,
  flat_model TEXT,
  lease_commence_date INTEGER,
  remaining_lease_years REAL,
  resale_price REAL,
  _resource_id TEXT,
  _ingested_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tr_month ON transactions_clean(month);
CREATE INDEX IF NOT EXISTS idx_tr_town  ON transactions_clean(town);
CREATE INDEX IF NOT EXISTS idx_tr_type  ON transactions_clean(flat_type);
