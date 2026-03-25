import json
import os
from groq import Groq
from models.schema import CompetitorIntel

MIN_CONFIDENCE = 0.4

class ValidationResult:
    def __init__(self, passed: bool, reason: str, revised_intel=None):
        self.passed = passed
        self.reason = reason
        self.revised_intel = revised_intel

def validate_intel(intel: CompetitorIntel) -> ValidationResult:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    if intel.confidence_score < MIN_CONFIDENCE:
        return ValidationResult(False, f"Confidence {intel.confidence_score:.2f} below {MIN_CONFIDENCE}")
    if len(intel.company_name.strip()) < 2:
        return ValidationResult(False, "Company name too short")
    for tier in intel.pricing_tiers:
        if tier.price_usd_monthly is not None:
            if tier.price_usd_monthly < 0 or tier.price_usd_monthly > 100_000:
                return ValidationResult(False, f"Invalid price in tier '{tier.name}'")

    summary = f"Company: {intel.company_name}\nURL: {intel.url}\nPricing: {[f'{t.name}: ${t.price_usd_monthly}/mo' for t in intel.pricing_tiers]}\nFree tier: {intel.has_free_tier}\nConfidence: {intel.confidence_score}"

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You are a data quality reviewer. Check for hallucinated or impossible data only.
IMPORTANT RULES:
- A free tier priced at $0.0/mo is completely valid and correct. Do NOT reject this.
- null price for Enterprise tier is valid and correct.
- Only reject if prices are negative, impossibly large, or company name is missing.
Respond ONLY with JSON: {"approved": true/false, "reason": "one sentence"}"""},
            {"role": "user", "content": summary}
        ],
        temperature=0.0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    review = json.loads(resp.choices[0].message.content)
    if not review.get("approved", False):
        return ValidationResult(False, f"LLM rejected: {review.get('reason')}")
    return ValidationResult(True, "Passed", revised_intel=intel)