from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
from datetime import datetime

class PricingTier(BaseModel):
    name: str
    price_usd_monthly: Optional[float] = None
    billing_cycle: Optional[str] = None
    key_features: list[str] = []

class CompetitorIntel(BaseModel):
    url: str
    company_name: str
    scraped_at: datetime
    pricing_tiers: list[PricingTier] = []
    has_free_tier: bool = False
    has_enterprise_tier: bool = False
    headline: Optional[str] = None
    key_features: list[str] = []
    new_features: list[str] = []
    primary_cta: Optional[str] = None
    target_persona: Optional[str] = None
    confidence_score: float = 0.0
    extraction_notes: str = ""

    @field_validator('confidence_score')
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))