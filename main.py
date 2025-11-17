import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Giftcard, Rate, Trade

app = FastAPI(title="Gift Card Trading API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Gift Card Trading API is live"}


@app.get("/test")
def test_database():
    """Quick check for DB connectivity"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Simple public endpoints for the app UI
@app.get("/api/rates")
def get_active_rates(brand: Optional[str] = None, country: Optional[str] = None):
    filt = {"is_active": True}
    if brand:
        filt["brand"] = brand
    if country:
        filt["country"] = country
    try:
        docs = get_documents("rate", filt, limit=200)
        # Convert ObjectId
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateTradeRequest(Trade):
    pass


@app.post("/api/trades")
def create_trade(payload: CreateTradeRequest):
    try:
        trade_dict = payload.model_dump()
        inserted_id = create_document("trade", trade_dict)
        return {"id": inserted_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brands")
def get_brands():
    try:
        docs = get_documents("giftcard", {"is_active": True}, limit=200)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        # Build unique brand list
        brands = sorted({d.get("brand") for d in docs if d.get("brand")})
        return {"items": brands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema")
def get_schema():
    """Expose schemas for the database viewer"""
    from inspect import getsource
    import schemas as schemas_module

    return {
        "schemas": {
            "User": getsource(User),
            "Giftcard": getsource(Giftcard),
            "Rate": getsource(Rate),
            "Trade": getsource(Trade),
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
