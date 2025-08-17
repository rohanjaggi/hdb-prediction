ingest:
	python3 data/ingest.py

transform:
	python3 data/transform-data.py

train:
	python3 model/train-xgb.py

serve:
	uvicorn api.app:app --reload --port 8000