from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import xgboost as xgb
import pandas as pd
import os
import uvicorn
from sqlalchemy import create_engine
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

model = None
town_mapping = {}
flat_type_mapping = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, town_mapping, flat_type_mapping
    
    model = xgb.Booster()
    model.load_model("model/xgb_model.json")
    
    eng = create_engine(os.getenv("DATABASE_URL"))
    
    towns = pd.read_sql("SELECT DISTINCT town, town_enc FROM transactions_clean", eng)
    town_mapping = dict(zip(towns['town'], towns['town_enc']))
    
    flats = pd.read_sql("SELECT DISTINCT flat_type, flat_type_enc FROM transactions_clean", eng)
    flat_type_mapping = dict(zip(flats['flat_type'], flats['flat_type_enc']))
    
    yield

app = FastAPI(title="HDB BTO Price Prediction API", version="1.0.0", lifespan=lifespan)

class PredictRequest(BaseModel):
    year: int
    month_num: int
    storey_median: int
    floor_area_sqm: int
    remaining_lease: int
    town: str
    flat_type: str

def predict_price(data: PredictRequest) -> float:
    town_enc = town_mapping.get(data.town.upper())
    flat_type_enc = flat_type_mapping.get(data.flat_type.upper())
    
    if town_enc is None:
        raise HTTPException(400, f"Unknown town")
    if flat_type_enc is None:
        raise HTTPException(400, f"Unknown flat type")
    
    features_dict = {
        'year': [data.year],
        'month_num': [data.month_num], 
        'storey_median': [data.storey_median],
        'floor_area_sqm': [data.floor_area_sqm],
        'remaining_lease': [data.remaining_lease],
        'town_enc': [town_enc],
        'flat_type_enc': [flat_type_enc]
    }
    df = pd.DataFrame(features_dict)
    dmatrix = xgb.DMatrix(df)
    price = model.predict(dmatrix)[0]

    return float(price)

@app.get("/")
def home():
    return {
        "message": "HDB Price Prediction API",
        "usage": "POST /predict with property details (year, month_num, storey_median, floor_area_sqm, remaining_lease, town, flat_type)"
    }

@app.post("/predict")
def predict(data: PredictRequest):
    if not model:
        raise HTTPException(503, "Model not loaded")
    
    try:
        price = predict_price(data)
        return {
            "predicted_price": round(price, 2),
            "property": data.model_dump()
        }
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/bto_price")
def bto_price(resale_price: float, discount: float = 20.0):
    bto = resale_price * (1 - discount/100)
    return {
        "resale_price": resale_price,
        "bto_price": round(bto, 2),
        "discount_percent": discount
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)