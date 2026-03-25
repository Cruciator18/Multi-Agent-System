import json
import os
from datetime import datetime, timezone
from groq import Groq
from models.schema import CompetitorIntel

EXTRACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "save_competitor_intel",
        "description": "Save structured competitive intelligence from a competitor webpage",
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "pricing_tiers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "price_usd_monthly": {"type": ["number", "null"]},
                            "billing_cycle": {"type": ["string", "null"]},
                            "key_features": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name"]
                    }
                },
                "has_free_tier": {"type": "boolean"},
                "has_enterprise_tier": {"type": "boolean"},
                "headline": {"type": ["string", "null"]},
                "key_features": {"type": ["array", "null"], "items": {"type": "string"}},
                "new_features": {"type": ["array", "null"], "items": {"type": "string"}},
                "primary_cta": {"type": ["string", "null"]},
                "target_persona": {"type": ["string", "null"]},
                "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "extraction_notes": {"type": "string"}
            },
            "required": ["company_name", "confidence_score", "extraction_notes"]
        }
    }
}

def extract_intel(url: str, cleaned_text: str) -> CompetitorIntel:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a competitive intelligence analyst. Extract structured data precisely. Do not hallucinate. Use null if info is missing."},
            {"role": "user", "content": f"URL: {url}\n\nCONTENT:\n{cleaned_text}"}
        ],
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "function", "function": {"name": "save_competitor_intel"}},
        temperature=0.1,
        max_tokens=2000,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    data = json.loads(tool_call.function.arguments)

    data["key_features"] = data.get("key_features") or []
    data["new_features"] = data.get("new_features") or []
    data["pricing_tiers"] = data.get("pricing_tiers") or []

    data["url"] = url
    data["scraped_at"] = datetime.now(timezone.utc)
    return CompetitorIntel(**data)