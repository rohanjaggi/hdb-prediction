from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import xgboost as xgb
import pandas as pd
import os
import uvicorn
import openai
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

model = None
town_mapping = {}
flat_type_mapping = {}

class PredictRequest(BaseModel):
    storey_median: int
    floor_area_sqm: int
    remaining_lease: int
    town: str
    flat_type: str

def predict_price(data: PredictRequest) -> float:
    town_enc = town_mapping.get(data.town.upper())
    flat_type_enc = flat_type_mapping.get(data.flat_type.upper())
    try:
        if town_enc is None:
            print(f"Unknown town: {data.town}")
            raise HTTPException(400, f"Unknown town")
        if flat_type_enc is None:
            print(f"Unknown flat type: {data.flat_type}")
            raise HTTPException(400, f"Unknown flat type")
        
        features_dict = {
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
    except Exception as e:
        print(f"pred error: {str(e)}")
        raise 

class HDBLLMService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = "deepseek/deepseek-r1"
        self.engine = create_engine(os.getenv("DATABASE_URL"))
    
    def get_bto_recommendations(self, years: int = 10) -> dict:
        with self.engine.connect() as c:
            query = text(f"""
            SELECT town, 
                   COUNT(*) as total_transactions,
                   COUNT(CASE WHEN year >= {2025-years} THEN 1 END) as recent_transactions,
                   AVG(resale_price) as avg_price
            FROM transactions_clean 
            WHERE resale_price IS NOT NULL
            GROUP BY town
            ORDER BY recent_transactions ASC, avg_price ASC
            LIMIT 10
            """)
            
            result = c.execute(query).fetchall()
            recommendations = [dict(row._mapping) for row in result]
            
            return {
                "period_analysed": f"({2025-years}-2025)",
                "recommendations": recommendations
            }
    
    def predict_bto_price(self, storey_median: int = 10, 
                     floor_area_sqm: int = 50, remaining_lease: int = 99, 
                     town: str = "ANG MO KIO", flat_type: str = "3 ROOM") -> dict:
        try:
            request = PredictRequest(
                storey_median=storey_median,
                floor_area_sqm=floor_area_sqm,
                remaining_lease=remaining_lease,
                town=town.upper(),
                flat_type=flat_type.upper()
            )
            
            resale_price = predict_price(request)
            bto_price = resale_price * 0.8  # 20% discount
            
            return {
                "storey_median": storey_median,
                "floor_area_sqm": floor_area_sqm,
                "remaining_lease": remaining_lease,
                "town": town,
                "flat_type": flat_type,
                "predicted_resale_price": round(resale_price, 0),
                "predicted_bto_price": round(bto_price, 0),
                "success": True
            }
            
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def calculate_affordability(self, price: float) -> dict:
        monthly_payment = price * 0.004  #very simple loan calc
        required_monthly_income = monthly_payment / 0.3  #30% of income rule
        #should add more depth to this calculation like adding down payment, interest rates, loan terms etc.

        if required_monthly_income <= 7000:
            category = "Low-Middle Income (<= $7k a month)"
        elif required_monthly_income <= 14000:
            category = "Middle Income ($7k-$14k a month)"
        else:
            category = "High Income (> $14k a month)"

        return {
            "price": round(price, 0),
            "monthly_payment": round(monthly_payment, 0),
            "required_monthly_income": round(required_monthly_income, 0),
            "income_category": category
        }
    
    def chat(self, user_prompt: str) -> str:
        analysis_prompt = f"""
You are a Singapore HDB housing analyst. Analyse this user query step by step:

USER QUERY: "{user_prompt}"

STEP 1: Identify what the user wants
- Do they want location recommendations?
- Do they want price predictions? 
- Do they want affordability analysis? 

STEP 2: Extract specific parameters
- Flat types mentioned: (3 ROOM, 4 ROOM, 5 ROOM, EXECUTIVE)
- Towns mentioned: (specific towns or "ALL" for recommendations)
- Floor levels: (low=1-5, middle=6-15, high=16+)
- Time period: (years mentioned or default 10)
- Floor area: (default 50 sqm if not specified otherwise)
- Years: (default 10 if not specified for recommendations)

STEP 3: Structure your analysis

Respond with ONLY this exact JSON format (no markdown, no explanations, no extra lines or text):
{{
    "reasoning": "Brief explanation of what user wants",
    "needs_recommendations": true/false,
    "needs_prediction": true/false, 
    "needs_affordability": true/false,
    "prediction_scenarios": [
        {{
            "flat_type": "3 ROOM",
            "town": "ANG MO KIO or ALL",
            "floor_levels": ["low", "middle", "high"],
            "floor_area_sqm": 50
        }}
    ],
    "years": 10
}}

EXAMPLES:
Query: "Recommend estates with limited BTO launches over the last 5 years"
→ needs_recommendations: true, needs_prediction: false, needs_affordability: false, years: 5

Query: "Look at the last 10 years of BTO launches and recommend estates with limited launches"
→ needs_recommendations: true, needs_prediction: false, needs_affordability: false, years: 10

Query: "How much for 4-room BTO in Tampines"  
→ needs_prediction: true, needs_affordability: false, needs_recommendations: false, town: "TAMPINES", flat_type: "4 ROOM"

Query: "How can I afford a 3-room flat"
→ needs_affordability: true, needs_prediction: true, needs_recommendations: false, flat_type: "3 ROOM"

Now analyse the user query above:
"""
        analysis_response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_completion_tokens=1500
        )
        
        try:
            print(analysis_response.choices[0].message.content)
            print(repr(analysis_response.choices[0].message.content))
            analysis = json.loads(analysis_response.choices[0].message.content)
            print(analysis)
            needs = analysis
        except Exception as e:
            return {"error": str(e), "success": False}
        
        function_results = []
        recommended_towns = []
        if needs.get("needs_recommendations", False):
            years = needs.get("years", 10)
            recommendations = self.get_bto_recommendations(years)
            function_results.append(f"BTO Recommendations:\n{json.dumps(recommendations, indent=2)}")
            recommended_towns = [rec["town"] for rec in recommendations.get("recommendations", [])]
        
        if needs.get("needs_prediction", False):
            prediction_scenarios = needs.get("prediction_scenarios", [])
            
            for scenario in prediction_scenarios:
                flat_type = scenario.get("flat_type")
                town_param = scenario.get("town")
                floor_levels = scenario.get("floor_levels", ["middle"])
                floor_area = scenario.get("floor_area_sqm", 50)
                
                if town_param == "ALL" and recommended_towns:
                    towns_to_analyse = recommended_towns[:5]
                elif town_param and town_param != "ALL":
                    towns_to_analyse = [town_param]
                else:
                    towns_to_analyse = ["ANG MO KIO"]  #as a fallback
                
                for town in towns_to_analyse:
                    for floor_level in floor_levels:
                        storey_mapping = {"low": 3, "middle": 10, "high": 20}
                        storey_median = storey_mapping.get(floor_level, 10)
                        
                        prediction = self.predict_bto_price(
                            flat_type=flat_type,
                            town=town,
                            floor_area_sqm=floor_area,
                            storey_median=storey_median
                        )
                        
                        prediction["scenario"] = f"{flat_type} in {town}- {floor_level}"
                        function_results.append(f"BTO Price Analysis:\n{json.dumps(prediction, indent=2)}")
                        
                        if prediction.get("success") and "predicted_bto_price" in prediction:
                            affordability = self.calculate_affordability(prediction["predicted_bto_price"])
                            affordability["scenario"] = f"Affordability for {prediction['scenario']}"
                            function_results.append(f"Affordability:\n{json.dumps(affordability, indent=2)}")
        
        has_recommendations = any("BTO Recommendations" in result for result in function_results)
        has_prices = any("BTO Price Analysis" in result for result in function_results)
        has_affordability = any("Affordability" in result for result in function_results)

        if has_recommendations and has_prices and has_affordability:
            system_prompt = """Create a CONCISE analysis (max 250 words) with these sections:
## Best BTO Locations
## Price Analysis  
## Affordability
## Next Steps
Use specific data provided. Be direct and actionable."""

        elif has_recommendations and has_prices:
            system_prompt = """Create a CONCISE analysis (max 250 words) with these sections:
## Best BTO Locations
## Price Analysis
## Next Steps
Use specific data provided. Be direct and actionable."""

        elif has_prices and has_affordability:
            system_prompt = """Create a CONCISE analysis (max 250 words) with these sections:
## Price Analysis
## Affordability
## Next Steps
Use specific data provided. Be direct and actionable."""

        elif has_recommendations:
            system_prompt = """Create a CONCISE analysis (max 250 words) with these sections:
## Best BTO Locations
## Next Steps
Use specific data provided. Be direct and actionable."""

        elif has_prices:
            system_prompt = """Create a CONCISE analysis (max 250 words) with these sections:
## Price Analysis
## Next Steps
Use specific data provided. Be direct and actionable."""

        else:
            system_prompt = """Provide general BTO guidance in under 100 words. Be helpful and actionable."""

        if function_results:
            context = f"{system_prompt}\n\nAnalysis data:\n{chr(10).join(function_results)}"
        else:
            context = system_prompt
        
        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_completion_tokens=1500
        )
        
        return final_response.choices[0].message.content

llm_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, town_mapping, flat_type_mapping, llm_service
    
    model = xgb.Booster()
    model.load_model("model/xgb_model.json")
    
    eng = create_engine(os.getenv("DATABASE_URL"))
    
    towns = pd.read_sql("SELECT DISTINCT town, town_enc FROM transactions_clean", eng)
    town_mapping = dict(zip(towns['town'], towns['town_enc']))
    
    flats = pd.read_sql("SELECT DISTINCT flat_type, flat_type_enc FROM transactions_clean", eng)
    flat_type_mapping = dict(zip(flats['flat_type'], flats['flat_type_enc']))
    
    llm_service = HDBLLMService()
    
    yield

app = FastAPI(title="HDB BTO Price Prediction API", version="1.0.0", lifespan=lifespan)

@app.get("/")
def home():
    return "HDB BTO Price Prediction API with AI"

@app.get("/health")
def health_check():
    return {
        "status": "ok" if model else "error",
        "model_loaded": model is not None,
    }

@app.post("/bto_price")
def bto_price(data: PredictRequest, discount: float = 20.0):
    if not model:
        raise HTTPException(503, "Model not loaded")
    
    try:
        price = predict_price(data)
        bto_price = price * (1 - discount / 100)
        return round(bto_price, 2)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/chat")
async def chat(request: Request):
    if not llm_service:
        raise HTTPException(503, "Model not loaded")
        
    try:
        prompt = await request.body()
        prompt_str = prompt.decode('utf-8')
        print(prompt_str)
        response = llm_service.chat(prompt_str)
        return {
            "response": response,
        }
    except Exception as e:
        raise HTTPException(500, f"Chat error: {str(e)}")

@app.get("/bto_recommendations")
def bto_recommendations():
    if not llm_service:
        raise HTTPException(503, "Model not loaded")

    try:
        recommendations = llm_service.get_bto_recommendations()
        return recommendations
    except Exception as e:
        raise HTTPException(500, f"Recommendation error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)