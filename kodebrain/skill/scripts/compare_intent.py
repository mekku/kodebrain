#!/usr/bin/env python3
"""
kodebrain compare-intent — deterministic intent↔observed comparison.

Reads accepted intent sources from ``intent-sources.json``, extracts claims,
and searches observed source files for agreement or contradiction.

Produces structured drift findings consumable by both the LLM onboard step
and the validate.py gate.

Usage:
  python3 compare_intent.py <root> --kb-dir docs/brain/projects/<name>/
  python3 compare_intent.py <root> --kb-dir ... --output findings.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frontmatter import parse as parse_frontmatter
from intent_inventory import _non_negotiable_principles


# ── claim extraction ─────────────────────────────────────────────────────

def _extract_technology_claims(doc_text: str) -> List[Dict]:
    """Find named technology/tool/library mentions in a spec.

    Looks for backtick-quoted terms, bolded names, and known technology
    pattern lines (e.g. 'uses Wispr', 'built with Express').
    """
    claims: List[Dict] = []
    seen: set = set()

    # Backtick-quoted identifiers: `Wispr`, `PostgreSQL`
    for m in re.finditer(r'`([A-Z][A-Za-z0-9._-]{2,})`', doc_text):
        name = m.group(1)
        if name not in seen and not name.startswith('_'):
            seen.add(name)
            claims.append({"claim": name, "type": "technology_reference", "evidence": m.group(0)})

    # **Bold** technology names in running text
    for m in re.finditer(r'\*\*([A-Z][A-Za-z0-9._-]{2,})\*\*', doc_text):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            claims.append({"claim": name, "type": "technology_reference", "evidence": m.group(0)})

    # Pattern: "uses X", "built with X", "runs on X"
    for m in re.finditer(
        r'(?:uses?|built\s+(?:with|on)|runs?\s+(?:on|with)|powered\s+by)\s+([A-Z][A-Za-z0-9._-]{2,})',
        doc_text
    ):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            claims.append({"claim": name, "type": "technology_choice", "evidence": m.group(0)})

    return claims


def _extract_state_machine_claims(doc_text: str) -> List[Dict]:
    """Find state machine definitions: states and transitions."""
    claims: List[Dict] = []

    # Pattern: idle → processing → done
    for m in re.finditer(
        r'([a-z_][a-z0-9_]*)\s*(?:→|->|→)\s*([a-z_][a-z0-9_]*)\s*(?:→|->|→)\s*([a-z_][a-z0-9_]*)',
        doc_text, re.IGNORECASE
    ):
        claims.append({
            "claim": f"state machine: {m.group(1)} → {m.group(2)} → {m.group(3)}",
            "type": "state_machine",
            "states": [m.group(1), m.group(2), m.group(3)],
            "evidence": m.group(0),
        })

    return claims


def _extract_data_model_fields(doc_text: str) -> List[Dict]:
    """Extract expected data model fields from spec.

    Pattern:
      ModelName:
        field: type
        field: type
    """
    claims: List[Dict] = []
    current_model: Optional[str] = None

    for line in doc_text.split('\n'):
        model_match = re.match(r'^(\w[ \w]*):\s*$', line)
        if model_match:
            current_model = model_match.group(1).strip()
            continue

        if current_model:
            field_match = re.match(r'^\s{2,}(\w+):\s*(.+)$', line)
            if field_match:
                claims.append({
                    "claim": f"{current_model}.{field_match.group(1)}",
                    "type": "data_model_field",
                    "model": current_model,
                    "field": field_match.group(1),
                    "expected_type": field_match.group(2).strip(),
                    "evidence": line.strip(),
                })
            elif line.strip() and not line.startswith(' '):
                # End of model block
                current_model = None

    return claims


# ── contradiction detection ──────────────────────────────────────────────

EXPLICIT_NEGATION = re.compile(
    r'(?:is\s+)?NOT\s+\w+|does\s+not\s+\w+|doesn\'t\s+\w+|'
    r'(?:hack|workaround|FIXME|TODO|XXX|HACK)[\s:]+',
    re.IGNORECASE
)


def _search_contradiction(claim: str, source_files: List[Path]) -> List[Dict]:
    """Search source files for evidence contradicting a claim.

    Returns list of contradiction findings (empty if none found).
    """
    findings: List[Dict] = []
    claim_lower = claim.lower()
    # Tokenize claim into searchable keywords
    keywords = [w for w in re.findall(r'[A-Za-z0-9_]{3,}', claim) if w.lower() not in ('the', 'and', 'for', 'with', 'that', 'this', 'from', 'all')]

    for sf in source_files:
        try:
            text = sf.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        text_lower = text.lower()

        # Check 1: Explicit negation near claim keywords
        negations = list(EXPLICIT_NEGATION.finditer(text))
        for neg in negations:
            neg_context = text[max(0, neg.start()-60):neg.end()+60]
            if any(kw.lower() in neg_context.lower() for kw in keywords):
                findings.append({
                    "source_file": str(sf),
                    "evidence": neg_context.strip().replace('\n', ' ')[:200],
                    "match_type": "explicit_negation",
                })

        # Check 2: Different technology name
        # If claim mentions a specific technology, check if source
        # uses a different one in the same role.
        # We look for comment annotations like "(spec says X)"
        spec_refs = re.findall(
            r'(?:spec|should|supposed to)\s+(?:says?\s+)?(\w+)',
            text, re.IGNORECASE
        )
        if spec_refs and any(kw.lower() in text_lower for kw in keywords):
            findings.append({
                "source_file": str(sf),
                "evidence": f"Source references spec expectation: {', '.join(spec_refs)}",
                "match_type": "spec_reference_in_source",
            })

        # Check 3: Missing expected field/pattern
        # For data model fields, check if the field name appears in source
        # (weak signal — absence doesn't prove contradiction)

    return findings


def _search_confirmation(claim: str, source_files: List[Path]) -> List[Dict]:
    """Search source for evidence confirming a claim."""
    findings: List[Dict] = []
    keywords = [w for w in re.findall(r'[A-Za-z0-9_]{3,}', claim)
                if w.lower() not in ('the', 'and', 'for', 'with', 'that', 'this', 'from', 'all')]

    if not keywords:
        return findings

    for sf in source_files:
        try:
            text = sf.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in text.lower())
        if matches >= len(keywords) * 0.5:  # At least half the keywords found
            findings.append({
                "source_file": str(sf),
                "keywords_matched": matches,
                "match_type": "confirmed_in_source",
            })

    return findings


# ── main comparison ──────────────────────────────────────────────────────

def _find_source_files(root: Path, exclude: List[str] | None = None) -> List[Path]:
    """Collect all source files in root, excluding non-source directories."""
    exclude = exclude or [
        'node_modules', '.git', 'dist', 'build', '__pycache__',
        '.venv', 'venv', '.tox', 'docs/brain',
    ]
    source_files: List[Path] = []
    for ext in ['.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go', '.java',
                '.rb', '.php', '.swift', '.kt', '.scala', '.cs', '.fs', '.ex', '.exs',
                '.c', '.cpp', '.h', '.hpp', '.css', '.scss', '.vue', '.svelte']:
        for f in root.rglob(f'*{ext}'):
            rel = str(f.relative_to(root))
            if any(rel.startswith(p) for p in exclude):
                continue
            source_files.append(f)
    return source_files


def compare_accepted_intent(root: Path, kb_dir: Path) -> Dict:
    """Read accepted intent sources, compare claims against observed source.

    Returns structured findings consumable by validate.py or the onboard step.
    """
    inventory_path = kb_dir / 'graph' / 'intent-sources.json'
    if not inventory_path.exists():
        return {
            "check": "intent-observed-comparison",
            "error": "intent-sources.json not found — run intent_inventory.py first",
        }

    inventory = json.loads(inventory_path.read_text())
    sources = inventory.get('sources', [])
    accepted = [s for s in sources if s['resolution']['state'] == 'accepted']

    if not accepted:
        return {
            "check": "intent-observed-comparison",
            "intent_sources_accepted": 0,
            "claims_checked": 0,
            "drift_items": [],
            "confirmed_items": [],
            "unverifiable_items": [],
            "summary": "No accepted intent sources — nothing to compare.",
        }

    source_files = _find_source_files(root)
    all_drift: List[Dict] = []
    all_confirmed: List[Dict] = []
    all_unverifiable: List[Dict] = []
    total_claims = 0

    for intent_src in accepted:
        doc_path = root / intent_src['path']
        if not doc_path.exists():
            continue

        try:
            doc_text = doc_path.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        # Extract claims
        tech_claims = _extract_technology_claims(doc_text)
        state_claims = _extract_state_machine_claims(doc_text)
        model_claims = _extract_data_model_fields(doc_text)
        principle_texts = _non_negotiable_principles(doc_text)
        principle_claims = [{"claim": p, "type": "non_negotiable_principle", "evidence": p}
                           for p in principle_texts]

        all_claims = tech_claims + state_claims + model_claims + principle_claims
        total_claims += len(all_claims)

        for claim in all_claims:
            contradictions = _search_contradiction(claim['claim'], source_files)
            confirmations = _search_confirmation(claim['claim'], source_files)

            if contradictions:
                all_drift.append({
                    "intent_source": intent_src['path'],
                    "claim": claim['claim'],
                    "claim_type": claim['type'],
                    "claim_evidence": claim.get('evidence', ''),
                    "contradictions": contradictions,
                    "severity": "HIGH" if claim['type'] in ('non_negotiable_principle', 'technology_choice')
                                else "MED",
                })
            elif confirmations:
                all_confirmed.append({
                    "intent_source": intent_src['path'],
                    "claim": claim['claim'],
                    "claim_type": claim['type'],
                    "confirmed_in": [c['source_file'] for c in confirmations],
                })
            else:
                all_unverifiable.append({
                    "intent_source": intent_src['path'],
                    "claim": claim['claim'],
                    "claim_type": claim['type'],
                })

    return {
        "check": "intent-observed-comparison",
        "intent_sources_accepted": len(accepted),
        "claims_checked": total_claims,
        "drift_count": len(all_drift),
        "confirmed_count": len(all_confirmed),
        "unverifiable_count": len(all_unverifiable),
        "drift_items": all_drift,
        "confirmed_items": all_confirmed,
        "unverifiable_items": all_unverifiable,
        "summary": (
            f"{len(all_drift)} drift, {len(all_confirmed)} confirmed, "
            f"{len(all_unverifiable)} unverifiable (of {total_claims} claims)"
        ),
    }


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain compare-intent — deterministic intent↔observed comparison",
    )
    parser.add_argument("root", help="Project root directory")
    parser.add_argument("--kb-dir", required=True,
                        help="KB project dir (reads intent-sources.json)")
    parser.add_argument("--output", "-o",
                        help="Write JSON to file instead of stdout")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f'Error: root "{root}" does not exist', file=sys.stderr)
        sys.exit(1)

    kb_dir = Path(args.kb_dir)
    result = compare_accepted_intent(root, kb_dir)

    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(json_str + "\n")
    print(json_str)


if __name__ == "__main__":
    main()
