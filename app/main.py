"""
FastAPI Backend for Smart Expense Categorizer
Provides ML-powered expense categorization, analytics, and predictions
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
from datetime import datetime

try:
    from .ml_models import ExpenseCategorizer, SpendingPredictor, AnomalyDetector
    from .data_processor import DataProcessor
except ImportError:
    from ml_models import ExpenseCategorizer, SpendingPredictor, AnomalyDetector
    from data_processor import DataProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Expense Categorizer API",
    description="ML-powered expense categorization and analytics API",
    version="1.0.0"
)

# CORS middleware
# Allow origins from environment variable or default to all for development
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML models
categorizer = ExpenseCategorizer()
predictor = SpendingPredictor()
anomaly_detector = AnomalyDetector()
data_processor = DataProcessor()

# Request models
class Transaction(BaseModel):
    description: str
    amount: float
    date: str
    transaction_type: Optional[str] = "DEBIT"

class CategorizeRequest(BaseModel):
    transactions: List[Transaction]

class AnalyticsRequest(BaseModel):
    data: List[Dict]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Smart Expense Categorizer API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "categorize": "/api/categorize",
            "batch_categorize": "/api/batch-categorize",
            "analytics": "/api/analytics",
            "predict": "/api/predict",
            "anomalies": "/api/anomalies"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload and process CSV file with transactions
    Automatically detects CSV format and maps columns
    """
    try:
        # Read CSV
        contents = await file.read()
        
        # Try different encodings
        try:
            df = pd.read_csv(pd.io.common.BytesIO(contents), encoding='utf-8')
        except:
            try:
                df = pd.read_csv(pd.io.common.BytesIO(contents), encoding='latin-1')
            except:
                df = pd.read_csv(pd.io.common.BytesIO(contents), encoding='cp1252')
        
        # Log original columns for debugging
        original_columns = list(df.columns)
        logger.info(f"Detected columns in CSV: {original_columns}")
        
        # Process data (with automatic format detection)
        processed_df = data_processor.process_dataframe(df)
        
        # Categorize transactions
        categorized_df = categorizer.categorize_batch(processed_df)
        
        # Detect anomalies
        anomalies = anomaly_detector.detect(processed_df)
        
        return {
            "success": True,
            "total_transactions": len(processed_df),
            "categories": categorized_df['Category'].value_counts().to_dict(),
            "anomalies_detected": len(anomalies),
            "data": categorized_df.to_dict(orient="records"),
            "original_columns": original_columns,
            "detected_format": "Auto-detected columns successfully"
        }
    except ValueError as e:
        # Handle specific format errors
        logger.error(f"Format error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"CSV Format Error: {str(e)}. Please ensure your CSV has Date, Description, and Amount columns."
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@app.post("/api/categorize")
async def categorize_transaction(transaction: Transaction):
    """
    Categorize a single transaction
    """
    try:
        category = categorizer.categorize(
            description=transaction.description,
            amount=transaction.amount
        )
        
        return {
            "category": category["category"],
            "confidence": category["confidence"],
            "suggestions": category.get("suggestions", [])
        }
    except Exception as e:
        logger.error(f"Categorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/batch-categorize")
async def batch_categorize(request: CategorizeRequest):
    """
    Categorize multiple transactions at once
    """
    try:
        results = []
        for tx in request.transactions:
            category = categorizer.categorize(
                description=tx.description,
                amount=tx.amount
            )
            results.append({
                "description": tx.description,
                "amount": tx.amount,
                "category": category["category"],
                "confidence": category["confidence"]
            })
        
        return {"results": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Batch categorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analytics")
async def get_analytics(data: List[Dict]):
    """
    Get spending analytics and insights
    """
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df = data_processor.process_dataframe(df)
        
        # Ensure Category column exists
        if 'Category' not in df.columns:
            df = categorizer.categorize_batch(df)
        
        # Calculate analytics
        total_spending = df[df['Transaction_Type'] == 'DEBIT']['Amount'].sum()
        total_income = df[df['Transaction_Type'] == 'CREDIT']['Amount'].sum()
        
        category_breakdown = df.groupby('Category')['Amount'].agg(['sum', 'mean', 'count']).to_dict('index')
        
        monthly_trends = df.groupby(df['Date'].dt.to_period('M'))['Amount'].sum().to_dict()
        
        return {
            "total_spending": float(total_spending),
            "total_income": float(total_income),
            "net_savings": float(total_income - total_spending),
            "category_breakdown": {k: {
                "total": float(v['sum']),
                "average": float(v['mean']),
                "count": int(v['count'])
            } for k, v in category_breakdown.items()},
            "monthly_trends": {str(k): float(v) for k, v in monthly_trends.items()},
            "top_categories": df.groupby('Category')['Amount'].sum().nlargest(5).to_dict()
        }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/predict")
async def predict_spending(data: List[Dict], days: int = Query(30, ge=1, le=365)):
    """
    Predict future spending patterns
    """
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df = data_processor.process_dataframe(df)
        
        predictions = predictor.predict(df, days=days)
        
        return {
            "predictions": predictions,
            "forecast_period": days,
            "trend": predictor.get_trend(df)
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/anomalies")
async def detect_anomalies(data: List[Dict]):
    """
    Detect anomalous transactions
    """
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df = data_processor.process_dataframe(df)
        
        anomalies = anomaly_detector.detect(df)
        
        return {
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies.to_dict(orient="records") if len(anomalies) > 0 else [],
            "risk_score": anomaly_detector.calculate_risk_score(df)
        }
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

