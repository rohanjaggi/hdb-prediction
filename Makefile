data:
	python3 data/ingest.py && python3 data/transform-data.py

train: data
	python3 model/train-xgb.py

serve:
	python3 api/app.py

test:
	python3 test/test-api.py

streamlit:
	streamlit run frontend/app.py

all: train serve streamlit