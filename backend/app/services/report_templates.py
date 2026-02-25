"""Custom report templates for PDF generation.

Provides template configurations that control PDF appearance:
colors, sections enabled, footer text, and language.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List

from app.models.db_factory import get_db_connection, SimpleDB


@dataclass
class ReportTemplate:
    """Report template configuration."""
    name: str
    header_color: str = "#1e40af"
    logo_path: Optional[str] = None
    sections_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "patient_info": True,
        "test_results": True,
        "fall_risk": True,
        "gait_pattern": True,
        "clinical_variables": True,
        "notes": True,
        "trend_charts": True,
        "comparison": True,
        "history": True,
    })
    footer_text: str = (
        "This report is generated automatically for clinical reference only. "
        "Please consult with a healthcare professional for diagnosis and treatment."
    )
    footer_text_ko: str = (
        "본 리포트는 임상 참고용으로 자동 생성되었습니다. "
        "진단 및 치료는 의료 전문가와 상담하세요."
    )
    language: str = "bilingual"  # "en", "ko", "bilingual"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReportTemplate":
        return cls(
            name=data.get("name", "custom"),
            header_color=data.get("header_color", "#1e40af"),
            logo_path=data.get("logo_path"),
            sections_enabled=data.get("sections_enabled", cls.__dataclass_fields__["sections_enabled"].default_factory()),
            footer_text=data.get("footer_text", cls.__dataclass_fields__["footer_text"].default),
            footer_text_ko=data.get("footer_text_ko", cls.__dataclass_fields__["footer_text_ko"].default),
            language=data.get("language", "bilingual"),
        )


# ===== Built-in templates =====

STANDARD_TEMPLATE = ReportTemplate(
    name="standard",
    header_color="#1e40af",
)

CLINICAL_TEMPLATE = ReportTemplate(
    name="clinical",
    header_color="#0f172a",
    sections_enabled={
        "patient_info": True,
        "test_results": True,
        "fall_risk": True,
        "gait_pattern": True,
        "clinical_variables": True,
        "notes": True,
        "trend_charts": True,
        "comparison": True,
        "history": True,
    },
    footer_text=(
        "CONFIDENTIAL - This detailed clinical report is for authorized medical personnel only. "
        "All patient data is protected under applicable privacy regulations."
    ),
    footer_text_ko=(
        "기밀 - 이 상세 임상 리포트는 허가된 의료진 전용입니다. "
        "모든 환자 데이터는 관련 개인정보 보호법에 의해 보호됩니다."
    ),
)

SUMMARY_TEMPLATE = ReportTemplate(
    name="summary",
    header_color="#059669",
    sections_enabled={
        "patient_info": True,
        "test_results": True,
        "fall_risk": True,
        "gait_pattern": False,
        "clinical_variables": False,
        "notes": False,
        "trend_charts": False,
        "comparison": True,
        "history": False,
    },
    footer_text="Brief summary report for quick reference.",
    footer_text_ko="간편 참조용 요약 리포트입니다.",
)

BUILTIN_TEMPLATES = {
    "standard": STANDARD_TEMPLATE,
    "clinical": CLINICAL_TEMPLATE,
    "summary": SUMMARY_TEMPLATE,
}


def get_template(name: str) -> ReportTemplate:
    """Get a template by name. Checks built-in first, then DB."""
    if name in BUILTIN_TEMPLATES:
        return BUILTIN_TEMPLATES[name]

    # Try DB
    db_template = _load_template_from_db(name)
    if db_template:
        return db_template

    return STANDARD_TEMPLATE


# ===== DB operations =====

def _ensure_table():
    """Create report_templates table if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_templates (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            config TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Run on import
_ensure_table()


def _load_template_from_db(name: str) -> Optional[ReportTemplate]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT config FROM report_templates WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        config = json.loads(row["config"])
        return ReportTemplate.from_dict(config)
    return None


def list_templates(include_builtin: bool = True) -> List[dict]:
    """List all templates (built-in + DB)."""
    results = []

    if include_builtin:
        for name, tmpl in BUILTIN_TEMPLATES.items():
            results.append({
                "id": None,
                "name": name,
                "builtin": True,
                "config": tmpl.to_dict(),
                "created_by": None,
                "created_at": None,
            })

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, config, created_by, created_at FROM report_templates ORDER BY created_at DESC")
    for row in cursor.fetchall():
        results.append({
            "id": row["id"],
            "name": row["name"],
            "builtin": False,
            "config": json.loads(row["config"]),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
        })
    conn.close()
    return results


def create_template(name: str, config: dict, created_by: str = None) -> dict:
    """Create a new custom template in DB."""
    if name in BUILTIN_TEMPLATES:
        raise ValueError(f"Cannot overwrite built-in template '{name}'")

    template_id = SimpleDB.generate_id()
    config_json = json.dumps(config, ensure_ascii=False)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO report_templates (id, name, config, created_by) VALUES (?, ?, ?, ?)",
        (template_id, name, config_json, created_by),
    )
    conn.commit()

    cursor.execute("SELECT id, name, config, created_by, created_at FROM report_templates WHERE id = ?", (template_id,))
    row = dict(cursor.fetchone())
    conn.close()

    row["config"] = json.loads(row["config"])
    row["builtin"] = False
    return row


def update_template(template_id: str, config: dict) -> Optional[dict]:
    """Update an existing custom template."""
    config_json = json.dumps(config, ensure_ascii=False)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE report_templates SET config = ? WHERE id = ?", (config_json, template_id))
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return None

    cursor.execute("SELECT id, name, config, created_by, created_at FROM report_templates WHERE id = ?", (template_id,))
    row = dict(cursor.fetchone())
    conn.close()

    row["config"] = json.loads(row["config"])
    row["builtin"] = False
    return row


def delete_template(template_id: str) -> bool:
    """Delete a custom template."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM report_templates WHERE id = ?", (template_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
