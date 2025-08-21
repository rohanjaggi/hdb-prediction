import os, json
import xgboost as xgb
import pandas as pd
import mlflow
import mlflow.xgboost
from sqlalchemy import create_engine
from sklearn.metrics import mean_absolute_error
from dotenv import load_dotenv
from datetime import datetime, UTC

load_dotenv()

DB_URL     = os.getenv("DATABASE_URL")
MODEL_PATH = os.path.join("model", "xgb_model.json")
META_PATH  = os.path.join("model", "xgb_meta.json")

FEATURES = [
    "storey_median",
    "floor_area_sqm",
    "remaining_lease",
    "town_enc", 
    "flat_type_enc",
]
TARGET = "resale_price"

def load_data():
    eng = create_engine(DB_URL, future=True)
    q = f"""
    SELECT {', '.join(FEATURES)}, {TARGET}, month
    FROM transactions_clean
    WHERE {TARGET} IS NOT NULL
      AND storey_median IS NOT NULL
      AND floor_area_sqm IS NOT NULL
      AND remaining_lease IS NOT NULL
      AND town_enc IS NOT NULL
      AND flat_type_enc IS NOT NULL
    """
    with eng.connect() as c:
        df = pd.read_sql(q, c)
    return df

def time_split(df: pd.DataFrame):
    train = df.sample(frac=0.7, random_state=42)
    remaining = df.drop(train.index)
    val = remaining.sample(frac=0.5, random_state=42)
    test = remaining.drop(val.index)
    return train, val, test

def dmatrix(df):
    X = df[FEATURES].astype(float)
    y = df[TARGET].astype(float)
    return xgb.DMatrix(X, label=y)

def main():
    df = load_data()
    train, val, test = time_split(df)

    dtrain, dval = dmatrix(train), dmatrix(val)

    params = {
        "objective": "reg:squarederror",
        "eval_metric": "mae",
        "max_depth": 6,          
        "eta": 0.03,              
        "subsample": 0.7,        
        "colsample_bytree": 0.7, 
        "lambda": 2.0,          
        "alpha": 0.5,            
        "seed": 42,
        "tree_method": "hist",
    } #played around with these params, and they seem to work well for the data, but more tuning could be done

    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_param("num_boost_round", 5000)
        mlflow.log_param("early_stopping_rounds", 100)
        mlflow.log_param("features", FEATURES)
        mlflow.log_param("target", TARGET)
        
        mlflow.log_metric("n_train", len(train))
        mlflow.log_metric("n_val", len(val))
        mlflow.log_metric("n_test", len(test))

        model = xgb.train(
            params=params,
            dtrain=dtrain,
            num_boost_round=5000,
            evals=[(dtrain,"train"), (dval,"val")],
            early_stopping_rounds=100,
            verbose_eval=200
        ) # experimented with a few diff models but xgboost came out on top and seems appropriate for this use case

        def mae(split):
            if len(split) == 0: return None
            return float(mean_absolute_error(split[TARGET], model.predict(xgb.DMatrix(split[FEATURES].astype(float)))))

        train_mae = mae(train)
        val_mae = mae(val)
        test_mae = mae(test) if len(test) else None
        best_iteration = int(getattr(model, "best_iteration", model.best_ntree_limit if hasattr(model, "best_ntree_limit") else 0))
        
        mlflow.log_metric("train_mae", train_mae)
        mlflow.log_metric("val_mae", val_mae)
        if test_mae:
            mlflow.log_metric("test_mae", test_mae)
        mlflow.log_metric("best_iteration", best_iteration)
        
        if train_mae and val_mae:
            overfitting_ratio = val_mae / train_mae
            mlflow.log_metric("overfitting_ratio", overfitting_ratio)
        
        input_example = train[FEATURES].head(1).astype(float)
        mlflow.xgboost.log_model(
            model, 
            name="model",
            registered_model_name="hdb_price_predictor",
            input_example=input_example,
            model_format="json"
        )

        metrics = {
            "train_mae": train_mae,
            "val_mae": val_mae,
            "test_mae": test_mae,
            "trained_at": datetime.now(UTC).isoformat() + "Z",
        } #should add more metrics for testing like maybe RMSE, R2, MAPE etc.
    
        model.save_model(MODEL_PATH)
        with open(META_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
        
        mlflow.log_artifact(MODEL_PATH)
        mlflow.log_artifact(META_PATH)
        
        print(f"MLflow run: {mlflow.active_run().info.run_id}")

        if os.path.exists("model/previous_metrics.json"):
            with open("model/previous_metrics.json", 'r') as f:
                prev_metrics = json.load(f)
            
            if metrics["test_mae"] < prev_metrics["test_mae"]:
                print("New model is better")
            else:
                print(" Previous model was better")
        
        with open("model/previous_metrics.json", "w") as f:
            json.dump(metrics, f)

if __name__ == "__main__":
    main()