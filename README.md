# HDB Price Prediction

## Setup Instructions

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. System Dependencies (macOS only)
If you're on macOS and get XGBoost errors, install OpenMP:
```bash
brew install libomp
```

### 3. Environment Variables
Create a `.env` file:
```
DATABASE_URL=sqlite:///hdb.db
```

### 4. Run the pipeline
```bash
# Ingest data
python3 data/ingest.py

# Transform data  
python3 data/transform-data.py

# Train model
python3 model/train-xgb.py
```

## Troubleshooting

### XGBoost Installation Issues
- **macOS**: `brew install libomp`
- **Windows**: Usually works without any other setup