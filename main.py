import os
from typing import List, Optional, Literal, Any, Dict
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Giftcard, Rate, Trade

app = FastAPI(title="Gift Card Trading API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utils ----------

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def admin_guard(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    required = os.getenv("ADMIN_KEY")
    if required and x_admin_key != required:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------- Health ----------

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


# ---------- Public Endpoints ----------

@app.get("/api/rates")
def get_active_rates(brand: Optional[str] = None, country: Optional[str] = None):
    filt: Dict[str, Any] = {"is_active": True}
    if brand:
        filt["brand"] = brand
    if country:
        filt["country"] = country
    try:
        docs = get_documents("rate", filt, limit=200)
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


@app.get("/api/trades")
def list_trades(email: Optional[str] = None, status: Optional[str] = None, limit: int = 200):
    try:
        filt: Dict[str, Any] = {}
        if email:
            filt["email"] = email
        if status:
            filt["status"] = status
        docs = get_documents("trade", filt, limit=limit)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brands")
def get_brands():
    try:
        docs = get_documents("giftcard", {"is_active": True}, limit=200)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        brands = sorted({d.get("brand") for d in docs if d.get("brand")})
        return {"items": brands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Admin Endpoints ----------

class UpdateTradeRequest(BaseModel):
    status: Optional[Literal["pending", "review", "approved", "rejected", "paid"]] = None
    notes: Optional[str] = None


@app.get("/api/admin/summary")
def admin_summary(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        return {
            "counts": {
                "users": db["user"].count_documents({}) if db else 0,
                "giftcards": db["giftcard"].count_documents({}) if db else 0,
                "rates": db["rate"].count_documents({}) if db else 0,
                "trades": db["trade"].count_documents({}) if db else 0,
                "pending_trades": db["trade"].count_documents({"status": "pending"}) if db else 0,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/trades")
def admin_list_trades(status: Optional[str] = None, limit: int = 200, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        filt: Dict[str, Any] = {}
        if status:
            filt["status"] = status
        docs = get_documents("trade", filt, limit=limit)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/admin/trades/{trade_id}")
def admin_update_trade(trade_id: str, payload: UpdateTradeRequest, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        update = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update:
            return {"updated": 0}
        update["updated_at"] = __import__("datetime").datetime.utcnow()
        result = db["trade"].update_one({"_id": to_object_id(trade_id)}, {"$set": update})
        return {"updated": result.modified_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateGiftcardRequest(Giftcard):
    pass


@app.post("/api/admin/brands")
def admin_create_brand(payload: CreateGiftcardRequest, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        new_id = create_document("giftcard", payload.model_dump())
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateGiftcardRequest(BaseModel):
    brand: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


@app.patch("/api/admin/brands/{brand_id}")
def admin_update_brand(brand_id: str, payload: UpdateGiftcardRequest, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        update = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update:
            return {"updated": 0}
        update["updated_at"] = __import__("datetime").datetime.utcnow()
        result = db["giftcard"].update_one({"_id": to_object_id(brand_id)}, {"$set": update})
        return {"updated": result.modified_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/brands")
def admin_list_brands(include_inactive: bool = True, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        filt: Dict[str, Any] = {} if include_inactive else {"is_active": True}
        docs = get_documents("giftcard", filt, limit=500)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateRateRequest(Rate):
    pass


@app.post("/api/admin/rates")
def admin_create_rate(payload: CreateRateRequest, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        new_id = create_document("rate", payload.model_dump())
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateRateRequest(BaseModel):
    brand: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    buy: Optional[float] = None
    sell: Optional[float] = None
    is_active: Optional[bool] = None


@app.patch("/api/admin/rates/{rate_id}")
def admin_update_rate(rate_id: str, payload: UpdateRateRequest, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        update = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update:
            return {"updated": 0}
        update["updated_at"] = __import__("datetime").datetime.utcnow()
        result = db["rate"].update_one({"_id": to_object_id(rate_id)}, {"$set": update})
        return {"updated": result.modified_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/rates")
def admin_list_rates(brand: Optional[str] = None, include_inactive: bool = True, x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")):
    admin_guard(x_admin_key)
    try:
        filt: Dict[str, Any] = {} if include_inactive else {"is_active": True}
        if brand:
            filt["brand"] = brand
        docs = get_documents("rate", filt, limit=500)
        for d in docs:
            d["_id"] = str(d.get("_id"))
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Schemas Introspection ----------

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
