"""
Database Schemas for Gift Card Trading App

Each Pydantic model corresponds to a MongoDB collection.
Collection name is the lowercase of the class name.

Collections:
- User: basic user profile
- Giftcard: supported gift card brands/types
- Rate: buy/sell rates for gift cards
- Trade: a submitted trade request by a user
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from datetime import datetime


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    is_verified: bool = Field(False, description="KYC/verification status")


class Giftcard(BaseModel):
    brand: str = Field(..., description="Brand name e.g. Amazon, iTunes, Steam")
    country: Optional[str] = Field(None, description="Country/Region e.g. US, UK")
    notes: Optional[str] = Field(None, description="Extra info users should know")
    is_active: bool = Field(True, description="Whether this card type is tradable")


class Rate(BaseModel):
    brand: str = Field(..., description="Gift card brand this rate applies to")
    country: Optional[str] = Field(None, description="Optional region/country")
    currency: Literal["USD", "NGN", "GHS", "KES", "GBP", "EUR"] = Field(
        "USD", description="Settlement currency"
    )
    buy: float = Field(..., gt=0, description="We buy at (per 1 unit of card currency)")
    sell: Optional[float] = Field(None, gt=0, description="We sell at (optional)")
    is_active: bool = Field(True)


class Trade(BaseModel):
    status: Literal["pending", "review", "approved", "rejected", "paid"] = Field(
        "pending", description="Current status of the trade"
    )
    brand: str = Field(..., description="Gift card brand")
    country: Optional[str] = Field(None, description="Region, if applicable")
    card_currency: Literal["USD", "GBP", "EUR", "CAD", "AUD", "NGN", "GHS"] = Field(
        ..., description="Gift card face value currency"
    )
    amount: float = Field(..., gt=0, description="Face value amount on the card")
    code: Optional[str] = Field(None, description="Gift card code (if text-based)")
    email: EmailStr = Field(..., description="User email to link the trade")
    phone: Optional[str] = Field(None, description="User phone")
    payout_currency: Literal["USD", "NGN", "GHS", "KES", "GBP", "EUR"] = Field(
        "NGN", description="Payout currency"
    )
    payout_method: Literal["bank", "wallet", "mobile_money"] = Field(
        "bank", description="How the user wants to be paid"
    )
    payout_details: Optional[str] = Field(
        None, description="Account/wallet details to receive funds"
    )
    notes: Optional[str] = Field(None)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
