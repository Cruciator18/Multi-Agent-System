import sqlite3
import json
from datetime import datetime
from pathlib import Path
from models.schema import CompetitorIntel

DB_PATH = Path("competitor_intel.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS competitor_intel (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT NOT NULL,
                company_name    TEXT,
                scraped_at      TEXT,
                pricing_tiers   TEXT,
                has_free_tier   INTEGER,
                has_enterprise  INTEGER,
                headline        TEXT,
                key_features    TEXT,
                new_features    TEXT,
                primary_cta     TEXT,
                target_persona  TEXT,
                confidence_score REAL,
                extraction_notes TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT,
                stage       TEXT,
                error_msg   TEXT,
                raw_output  TEXT,
                logged_at   TEXT DEFAULT (datetime('now'))
            )
        """)

def save_intel(intel: CompetitorIntel) -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO competitor_intel
            (url, company_name, scraped_at, pricing_tiers, has_free_tier,
             has_enterprise, headline, key_features, new_features,
             primary_cta, target_persona, confidence_score, extraction_notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            intel.url,
            intel.company_name,
            intel.scraped_at.isoformat(),
            json.dumps([t.model_dump() for t in intel.pricing_tiers]),
            int(intel.has_free_tier),
            int(intel.has_enterprise_tier),
            intel.headline,
            json.dumps(intel.key_features),
            json.dumps(intel.new_features),
            intel.primary_cta,
            intel.target_persona,
            intel.confidence_score,
            intel.extraction_notes,
        ))
        return cursor.lastrowid

def log_error(url: str, stage: str, error_msg: str, raw_output: str = ""):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO error_log (url, stage, error_msg, raw_output)
            VALUES (?,?,?,?)
        """, (url, stage, error_msg, raw_output))