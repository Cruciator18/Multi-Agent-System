import os
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from agents.scraper import fetch_and_clean
from agents.extractor import extract_intel
from agents.validator import validate_intel
from database.db import initialize_db, save_intel, log_error
from pydantic import ValidationError


COMPETITOR_URLS = [
    "https://linear.app/pricing",
    "https://www.notion.so/pricing",
    "https://clickup.com/pricing",
]

def run_pipeline(url: str) -> dict:
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {url}")
    print('='*60)

    print("  [Agent 1] Scraping and cleaning HTML...")
    try:
        cleaned_text = fetch_and_clean(url)
        print(f"  [Agent 1] ✓ Cleaned text: {len(cleaned_text)} chars")
    except Exception as e:
        log_error(url, "scraper", str(e))
        return {"url": url, "status": "failed", "stage": "scraper", "error": str(e)}

    print("  [Agent 2] Extracting structured intel...")
    try:
        intel = extract_intel(url, cleaned_text)
        print(f"  [Agent 2] ✓ Extracted: {intel.company_name} | "
              f"{len(intel.pricing_tiers)} tiers | "
              f"confidence: {intel.confidence_score:.2f}")
    except ValidationError as e:
        log_error(url, "extractor", f"Pydantic validation failed: {e}", cleaned_text[:500])
        return {"url": url, "status": "failed", "stage": "extractor", "error": str(e)}
    except Exception as e:
        log_error(url, "extractor", str(e), cleaned_text[:500])
        return {"url": url, "status": "failed", "stage": "extractor", "error": str(e)}

    print("  [Agent 3] Validating against schema and business rules...")
    try:
        result = validate_intel(intel)
    except Exception as e:
        log_error(url, "validator", str(e))
        return {"url": url, "status": "failed", "stage": "validator", "error": str(e)}

    if not result.passed:
        print(f"  [Agent 3] ✗ Rejected: {result.reason}")
        log_error(url, "validator", result.reason)
        return {"url": url, "status": "rejected", "reason": result.reason}

    final_intel = result.revised_intel or intel
    row_id = save_intel(final_intel)
    print(f"  [DB]      ✓ Saved to database (row id: {row_id})")
    
    return {
        "url": url,
        "status": "success",
        "company": final_intel.company_name,
        "row_id": row_id,
        "confidence": final_intel.confidence_score,
        "tiers": [t.name for t in final_intel.pricing_tiers],
    }

def main():
    initialize_db()
    print(f"Database initialized.")
    print(f"Running pipeline for {len(COMPETITOR_URLS)} URLs...\n")
    
    results = []
    for url in COMPETITOR_URLS:
        result = run_pipeline(url)
        results.append(result)
    
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print('='*60)
    
    success = [r for r in results if r["status"] == "success"]
    failed  = [r for r in results if r["status"] != "success"]
    
    print(f"  ✓ Successful: {len(success)}/{len(results)}")
    for r in success:
        print(f"      {r['company']} — {len(r.get('tiers', []))} pricing tiers "
              f"(confidence: {r['confidence']:.0%})")
    
    if failed:
        print(f"  ✗ Failed/Rejected: {len(failed)}")
        for r in failed:
            print(f"      {r['url']} — {r.get('reason') or r.get('error')}")

if __name__ == "__main__":
    main()