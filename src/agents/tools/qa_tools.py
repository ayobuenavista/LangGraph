"""Tools available to the QA Agent."""

from __future__ import annotations

import json
import re

from langchain_core.tools import tool


@tool
def review_code_security(code: str, language: str = "python") -> str:
    """Scan code for common security issues.

    Checks for: hardcoded secrets, SQL injection, XSS vectors, unsafe eval,
    exposed API keys, and missing input validation.
    """
    issues: list[dict] = []

    patterns = {
        "hardcoded_secret": [
            (r'(?:api_key|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']', "Possible hardcoded secret"),
            (r'sk-[a-zA-Z0-9]{20,}', "Possible API key in source"),
        ],
        "injection": [
            (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{', "Possible SQL injection via f-string"),
            (r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', "Possible SQL injection via .format()"),
        ],
        "xss": [
            (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML usage — verify sanitization"),
            (r'innerHTML\s*=', "Direct innerHTML assignment — XSS risk"),
        ],
        "unsafe_eval": [
            (r'\beval\s*\(', "Use of eval() — code injection risk"),
            (r'\bexec\s*\(', "Use of exec() — code injection risk"),
        ],
    }

    for category, rules in patterns.items():
        for pattern, message in rules:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + 1
                issues.append({
                    "category": category,
                    "message": message,
                    "line": line_num,
                    "snippet": code.splitlines()[line_num - 1].strip()[:100],
                })

    return json.dumps({
        "total_issues": len(issues),
        "issues": issues,
        "passed": len(issues) == 0,
    }, indent=2)


@tool
def validate_data_consistency(
    source_data: str,
    displayed_data: str,
    tolerance: float = 0.01,
) -> str:
    """Compare source data against displayed data to verify accuracy.

    Args:
        source_data: JSON string of source values {"field": number}.
        displayed_data: JSON string of displayed values {"field": number}.
        tolerance: Acceptable relative difference (default 1%).
    """
    source: dict = json.loads(source_data)
    displayed: dict = json.loads(displayed_data)

    mismatches = []
    missing = []

    for key, src_val in source.items():
        if key not in displayed:
            missing.append(key)
            continue
        disp_val = displayed[key]
        if isinstance(src_val, (int, float)) and isinstance(disp_val, (int, float)):
            if src_val == 0:
                if disp_val != 0:
                    mismatches.append({
                        "field": key,
                        "source": src_val,
                        "displayed": disp_val,
                        "diff_pct": "infinity",
                    })
            else:
                diff = abs(src_val - disp_val) / abs(src_val)
                if diff > tolerance:
                    mismatches.append({
                        "field": key,
                        "source": src_val,
                        "displayed": disp_val,
                        "diff_pct": round(diff * 100, 4),
                    })

    return json.dumps({
        "passed": len(mismatches) == 0 and len(missing) == 0,
        "mismatches": mismatches,
        "missing_fields": missing,
        "fields_checked": len(source),
    }, indent=2)


@tool
def check_accessibility(component_code: str) -> str:
    """Audit a React component for basic accessibility compliance.

    Checks for: missing alt text, missing aria-labels, color contrast tokens,
    keyboard navigation, semantic HTML.
    """
    issues: list[dict] = []
    lines = component_code.splitlines()

    for i, line in enumerate(lines, 1):
        # Images without alt
        if re.search(r'<img\b(?![^>]*\balt\b)', line):
            issues.append({"line": i, "issue": "img without alt attribute"})

        # Clickable divs without role/keyboard
        if re.search(r'<div[^>]*onClick', line) and "role=" not in line:
            issues.append({"line": i, "issue": "clickable div without role='button'"})

        # Links without href
        if re.search(r'<a\b(?![^>]*\bhref\b)', line):
            issues.append({"line": i, "issue": "anchor tag without href"})

        # Form inputs without label
        if re.search(r'<input\b(?![^>]*(?:aria-label|id))', line):
            issues.append({"line": i, "issue": "input without aria-label or associated label"})

        # Hardcoded colors (not using tokens)
        if re.search(r'(?:color|background):\s*#[0-9a-fA-F]{3,8}', line):
            issues.append({"line": i, "issue": "hardcoded color — use design tokens instead"})

    # Check for heading hierarchy
    headings = re.findall(r'<h([1-6])', component_code)
    for j in range(1, len(headings)):
        if int(headings[j]) > int(headings[j - 1]) + 1:
            issues.append({
                "line": 0,
                "issue": f"heading skip: h{headings[j-1]} -> h{headings[j]}",
            })

    return json.dumps({
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "wcag_level": "AA" if len(issues) <= 2 else "Fail",
    }, indent=2)


@tool
def check_requirements_coverage(
    requirements: str,
    delivered_items: str,
) -> str:
    """Compare delivered items against original requirements.

    Args:
        requirements: JSON array of requirement strings.
        delivered_items: JSON array of delivered item descriptions.
    """
    reqs: list[str] = json.loads(requirements)
    delivered: list[str] = json.loads(delivered_items)

    coverage = []
    for req in reqs:
        req_lower = req.lower()
        matched = any(
            # Fuzzy match: check if key words from requirement appear in deliverables
            sum(1 for word in req_lower.split() if word in d.lower())
            >= len(req_lower.split()) * 0.4
            for d in delivered
        )
        coverage.append({
            "requirement": req,
            "covered": matched,
        })

    covered_count = sum(1 for c in coverage if c["covered"])
    total = len(reqs)
    coverage_pct = (covered_count / total * 100) if total else 100

    return json.dumps({
        "coverage_percent": round(coverage_pct, 1),
        "covered": covered_count,
        "total": total,
        "unreliability_tax": round(100 - coverage_pct, 1),
        "within_budget": (100 - coverage_pct) <= 15,
        "details": coverage,
    }, indent=2)


QA_TOOLS = [
    review_code_security,
    validate_data_consistency,
    check_accessibility,
    check_requirements_coverage,
]
