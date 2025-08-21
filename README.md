# HDB BTO Price Prediction API

### NOTE for GovTech: I was given an extension for this project as I was travelling overseas to start my semester exchange programme till Aug 21

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. System Dependencies (macOS only)
If on macOS and get XGBoost errors:
```bash
brew install libomp
```

### 3. Environment Setup
Create a `.env` file with your API key:
```bash
echo "DATABASE_URL=sqlite:///hdb.db"
echo "OPENROUTER_API_KEY=your_openai_api_key_here" 
("sample key for testing": "sk-or-" + "v1-478d29af6f1d56bc5" + "234a65739b8d2b5a0ffa5af326" + "a69622e0e809c79dcde2d")
```
NOTE: The service uses DeepSeek R1, by OpenRouter (free to use)

### 4. Run the Pipeline
```bash
make data
make train   # Train model
make serve   
```

### 5. Test the System
```bash
make test

make health
```

### 6. Start the Frontend
```bash
make streamlit
```

## 🎯 Usage

### API Endpoints
- **Health Check**: `GET http://localhost:8000/health`
- **Price Prediction**: `POST http://localhost:8000/bto_price`
- **AI Chat**: `POST http://localhost:8000/chat`
- **BTO Recommendations**: `GET http://localhost:8000/bto_recommendations`

### Frontend Interface
- **Streamlit App**: `http://localhost:8501`

## Architecture & Design Choices

### Data Pipeline
- **Source**: Real HDB transaction data from data.gov.sg (HDB Resale Prices dataset: 2015-Present)
- **Storage**: SQLite database for simplicity
- **Processing**: Pandas for data transformation and feature engineering
- **Automation**: Makefile-driven pipeline for reproducible builds

#### Feature Importance (Typical for HDB pricing)
1. **Town** - Location is typically the strongest predictor
2. **Floor Area** - Size directly correlates with price  
3. **Flat Type** - Room count affects pricing
4. **Storey Level** - Higher floors may command premium
5. **Remaining Lease** - Lease duration impacts value
6. Year and month were removed to make the model more accurate to unseen data (model was overfitting)

### Machine Learning Model
- **Algorithm**: XGBoost Regression
- **Features**: Town, flat type, floor area, storey level, remaining lease
- **Encoding**: Label encoding for categorical variables (town and flat type)

### API Design
- **Framework**: FastAPI
- **Architecture**: RESTful API with endpoint separation
- **Response Format**: JSON responses with error handling

### LLM Integration
- **Provider**: DeepSeek R1 by OpenRouter for natural language understanding
- **Function Calling**: Structured analysis of user queries

### Database Schema
```sql
-- cleaned and processed data
transactions_clean (
    id, month, year, month_num,
    town, town_enc, flat_type, flat_type_enc,
    block, street_name, storey_range, storey_median,
    floor_area_sqm, flat_model, lease_commence_date,
    remaining_lease, resale_price,
    _resource_id, _ingested_at
)

-- Raw data
transactions_raw (
    month, town, flat_type, block, street_name,
    storey_range, floor_area_sqm, flat_model,
    lease_commence_date, remaining_lease, resale_price,
    _resource_id, _ingested_at
)
```

## Extensions & Improvements

### Immediate Extensions
- **More Data Sources & Better Model Features**: Integrate school rankings, MRT distances, amenities and experiment with other model features to boost prediction accuracy
- **Deployment**: Deploy to production for live usage
- **Advanced Models**: Try other models like ensemble methods, neural nets
- **Caching**: Redis for faster repeated predictions
- **Better AI Models**: Using paid models like OpenAI 4o for more reliable queries

### Data Science Improvements
- **A/B Testing**: Multiple model versions for comparison
- **Drift Detection**: Automated model retraining triggers

## AI Chat Features

The LLM integration provides intelligent responses to queries like:
- "What are the cheapest BTO locations?"
- "How much income do I need for a 4-room flat?"
- "Compare prices between Sengkang and Punggol"
- "Which towns have limited BTO launches recently?"