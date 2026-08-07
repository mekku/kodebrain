#!/usr/bin/env python3
"""Deterministic onboard validation gate.

Runs 6 checks against a compiled KB and produces validation-result.json.
Same KB → same result. No NLP.

Usage:
  python3 validate.py <kb_dir> [--project-root <root>] [--output <path>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from frontmatter import parse as parse_frontmatter


# ── helpers ──────────────────────────────────────────────────────────

def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def load_md(path: Path) -> str:
    with open(path) as f:
        return f.read()


def resolve_page_path(kb_dir: Path, page_path: str) -> Optional[Path]:
    """Resolve a page_path from nodes.json to an actual file.
    page_path is relative to docs/brain/projects/ and starts with project name.
    kb_dir is docs/brain/projects/<project>/."""
    if not page_path:
        return None
    p = Path(page_path)
    # Strip leading project name segment if it matches kb_dir name
    parts = p.parts
    if parts and parts[0] == kb_dir.name:
        p = Path(*parts[1:])
    full = kb_dir / p
    return full if full.exists() else None


def find_md_files(kb_dir: Path) -> List[Path]:
    return sorted(p for p in kb_dir.rglob("*.md") if p.is_file())


def extract_section(text: str, heading: str) -> Optional[str]:
    """Extract content under a markdown heading."""
    # Find the heading line, then collect content until next heading of same or higher level
    heading_re = re.compile(rf"^(#+)\s+{re.escape(heading)}\s*$", re.MULTILINE)
    m = heading_re.search(text)
    if not m:
        return None
    heading_level = len(m.group(1))
    start = m.end()
    # Find next heading of same or higher level
    next_heading = re.compile(rf"^#{{{1,{heading_level}}}}\s+", re.MULTILINE)
    nm = next_heading.search(text, start)
    end = nm.start() if nm else len(text)
    return text[start:end].strip()


def has_section(text: str, heading: str) -> bool:
    return extract_section(text, heading) is not None


def extract_table_rows(text: str, section_heading: str) -> List[Dict[str, str]]:
    """Extract rows from a markdown table under a given section heading."""
    section = extract_section(text, section_heading)
    if not section:
        return []

    rows = []
    lines = section.strip().split("\n")
    headers: List[str] = []

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells = [c for c in cells if c]  # remove empties from leading/trailing pipes

        if not cells:
            continue

        # Skip separator rows (|---|---|)
        if all(re.match(r"^-+$", c) for c in cells):
            continue

        if not headers:
            headers = cells
        else:
            row = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row[headers[i]] = cell
            if row:
                rows.append(row)

    return rows


def extract_enum_values(text: str) -> List[str]:
    """Extract enum-like values from inline code or table cells.
    Looks for patterns like `active`, `superseded`, `deprecated` in lifecycle sections."""
    enums: List[str] = []
    # Backtick-wrapped values
    for m in re.finditer(r"`([a-z_]+)`", text):
        val = m.group(1)
        if re.match(r"^[a-z][a-z_]+$", val) and len(val) > 3:
            enums.append(val)
    return enums


def has_subsection(text: str, section: str, subsection: str) -> bool:
    """Check if a markdown section has a subsection heading."""
    sec = extract_section(text, section)
    if not sec:
        return False
    return bool(re.search(rf"^#+\s+{re.escape(subsection)}\s*$", sec, re.MULTILINE))


# ── canonical source registry ────────────────────────────────────────

def build_canonical_registry(project_root: Path) -> Dict[str, Dict]:
    """Derive canonical registry from spec frontmatter — not a handwritten copy.

    Scans docs/design/spec/*.md for spec_role=canonical|canonical-root,
    reads owns[] and exports (if present). One concept → one canonical owner.
    """
    spec_dir = project_root / "docs" / "design" / "spec"
    if not spec_dir.is_dir():
        return {}

    registry: Dict[str, Dict] = {}
    for spec_file in sorted(spec_dir.glob("*.md")):
        try:
            text = spec_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        role = fm.get("spec_role", "")
        if role not in ("canonical", "canonical-root"):
            continue

        rel_path = str(spec_file.relative_to(project_root))

        # Read owns[] from frontmatter
        owns_raw = fm.get("owns", [])
        owns: List[str] = []
        if isinstance(owns_raw, list):
            owns = [str(o) for o in owns_raw]
        elif isinstance(owns_raw, str) and owns_raw:
            owns = [o.strip() for o in owns_raw.split(",") if o.strip()]

        # Read exports from frontmatter (concept → section mapping)
        exports_raw = fm.get("exports", {})
        exports: Dict[str, str] = {}
        if isinstance(exports_raw, dict):
            exports = {str(k): str(v) for k, v in exports_raw.items()}

        # Enum sections: if exports declared in frontmatter, use exclusively.
        # If exports key absent, auto-detect. This lets specs opt out of
        # auto-detection by setting `exports: {}`.
        enum_sections: List[str] = []
        if "exports" in fm:
            enum_sections = list(exports.values())
        else:
            # Auto-detect: any H2/H3 heading that contains a table
            # with backtick-wrapped values (lifecycle state pattern)
            heading_re = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)
            table_re = re.compile(r"^\|.+\|$", re.MULTILINE)
            for hm in heading_re.finditer(body):
                heading = hm.group(2).strip()
                heading_level = len(hm.group(1))
                section_start = hm.end()
                next_h = re.compile(
                    rf"^#{{{1,{heading_level}}}}\s+", re.MULTILINE
                )
                nm = next_h.search(body, section_start)
                section_end = nm.start() if nm else len(body)
                section_body = body[section_start:section_end]
                if table_re.search(section_body):
                    backtick_vals = extract_enum_values(section_body)
                    if len(backtick_vals) >= 3:
                        enum_sections.append(heading)

        registry[rel_path] = {
            "owns": owns,
            "exports": exports,
            "enum_sections": enum_sections,
        }

    return registry


# ── Check 1: Referential Integrity ───────────────────────────────────

def check_referential_integrity(kb_dir: Path, diagnostics: List[Dict], nodes_map: Dict[str, Any]) -> List[Dict]:
    """Consume compiler diagnostics for orphan wiki-links.
    Uses node.page_path to verify file existence — does NOT guess filesystem layout from node ID."""
    findings = []
    for diag in diagnostics:
        if diag.get("type") != "orphan_wikilink":
            continue
        target = diag.get("target", "")
        source = diag.get("source", "")
        edge_type = diag.get("edge_type", "related_to")

        # Verify against actual file via page_path
        target_node = nodes_map.get(target)
        if target_node:
            page_path = target_node.get("page_path", "")
            if page_path:
                actual_path = resolve_page_path(kb_dir, page_path)
                if actual_path and actual_path.exists():
                    continue  # false positive — page exists at node's declared path

        section = diag.get("section", "")
        # Classify severity
        severity = "ERROR" if is_required_reference(edge_type, source, nodes_map, section) else "REVIEW"

        finding = {
            "check": "referential-integrity",
            "severity": severity,
            "rule": "orphan-wikilink",
            "source_node": source,
            "target": target,
            "edge_type": edge_type,
            "description": f"Wiki-link target '{target}' does not exist (linked from '{source}' via '{edge_type}')",
        }

        if severity == "ERROR":
            finding["id"] = f"ERR-REF-{len([f for f in findings if f['severity']=='ERROR'])+1:03d}"
        else:
            finding["id"] = f"REV-REF-{len([f for f in findings if f['severity']=='REVIEW'])+1:03d}"

        findings.append(finding)

    return findings


def is_required_reference(edge_type: str, source: str, nodes_map: Dict, section: str = "") -> bool:
    """Determine if a reference is required (missing = ERROR) vs optional (missing = REVIEW)."""
    # References from Active Changes section → required
    if section and "active change" in section.lower():
        return True

    # Domain dependency → required
    if edge_type == "depends_on":
        return True

    # Risk reference → required
    if edge_type == "has_caveat" or edge_type == "risky_for":
        return True

    # References from project hub required sections
    if edge_type in ("references",) and source.endswith("kodebrain"):
        return True

    return False


# ── Check 2: Required Artifact Integrity ─────────────────────────────

def check_required_artifacts(kb_dir: Path, nodes: List[Dict]) -> List[Dict]:
    findings = []
    project_name = kb_dir.name

    # Project hub
    hub = kb_dir / f"{project_name}.md"
    if not hub.exists():
        findings.append({
            "id": "ERR-ART-001",
            "check": "required-artifact-integrity",
            "severity": "ERROR",
            "rule": "missing-required-page",
            "target": str(hub.relative_to(kb_dir)),
            "description": f"Project hub '{project_name}.md' is missing",
        })

    # Domain hubs for every declared domain
    domains_dir = kb_dir / "domains"
    if domains_dir.exists():
        for domain_dir in domains_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            domain_slug = domain_dir.name
            domain_hub = domain_dir / f"{domain_slug}.md"
            if not domain_hub.exists():
                findings.append({
                    "id": f"ERR-ART-{len(findings)+1:03d}",
                    "check": "required-artifact-integrity",
                    "severity": "ERROR",
                    "rule": "missing-required-page",
                    "target": str(domain_hub.relative_to(kb_dir)),
                    "description": f"Domain hub for '{domain_slug}' is missing",
                })

    # Graph indexes
    for graph_file in ["nodes.json", "edges.json", "file-index.json"]:
        gf = kb_dir / "graph" / graph_file
        if not gf.exists():
            findings.append({
                "id": f"ERR-ART-{len(findings)+1:03d}",
                "check": "required-artifact-integrity",
                "severity": "ERROR",
                "rule": "missing-required-page",
                "target": f"graph/{graph_file}",
                "description": f"Graph index '{graph_file}' is missing",
            })

    # file-hashes.json
    fh = kb_dir / "graph" / "file-hashes.json"
    if not fh.exists():
        findings.append({
            "id": f"REV-ART-{len(findings)+1:03d}",
            "check": "required-artifact-integrity",
            "severity": "REVIEW",
            "rule": "missing-required-page",
            "target": "graph/file-hashes.json",
            "description": "File hashes index is missing — can be regenerated via harvest",
        })

    return findings


# ── Check 3: Provenance/Confidence Consistency ────────────────────────

def check_provenance_consistency(kb_dir: Path, nodes: List[Dict]) -> List[Dict]:
    findings = []
    for node in nodes:
        provenance = node.get("provenance", "")
        confidence = node.get("confidence", "")
        knowledge_role = node.get("knowledge_role", "")
        source_files = node.get("source_files", [])
        node_id = node.get("id", "unknown")

        # Rule: provenance=human + confidence=verified requires human evidence
        if provenance == "human" and confidence == "verified":
            page_path = node.get("page_path", "")
            if page_path:
                full_path = resolve_page_path(kb_dir, page_path)
                if full_path:
                    body = load_md(full_path)
                    # Must be an actual human-note block, not a mention in prose
                    has_human_note = bool(re.search(r'(?:^|\n)\s*<!--\s*human-note', body))
                    # Interview evidence requires explicit markers, not just the word "interview"
                    has_interview = any(phrase in body.lower() for phrase in [
                        "interview transcript", "human-provided:", "human input:",
                        "provided by user", "user confirmed", "human confirmed"
                    ])
                    if not has_human_note and not has_interview:
                        findings.append({
                            "id": f"ERR-PRV-{len(findings)+1:03d}",
                            "check": "provenance-consistency",
                            "severity": "ERROR",
                            "rule": "invalid-provenance",
                            "node": node_id,
                            "description": f"Node has provenance=human + confidence=verified but no human-note block or interview evidence",
                        })

        # Rule: provenance=source_code + confidence=verified is invalid
        if provenance == "source_code" and confidence == "verified":
            findings.append({
                "id": f"ERR-PRV-{len(findings)+1:03d}",
                "check": "provenance-consistency",
                "severity": "ERROR",
                "rule": "invalid-provenance",
                "node": node_id,
                "description": "Node has provenance=source_code + confidence=verified. 'verified' is human-only.",
            })

        # Rule: provenance=generated + confidence=supported or verified is invalid
        if provenance == "generated" and confidence in ("supported", "verified"):
            findings.append({
                "id": f"ERR-PRV-{len(findings)+1:03d}",
                "check": "provenance-consistency",
                "severity": "ERROR",
                "rule": "invalid-provenance",
                "node": node_id,
                "description": f"Node has provenance=generated + confidence={confidence}. Generated content cannot claim 'supported' or 'verified'.",
            })

        # Rule: knowledge_role=intent + source_files with deprecated status
        if knowledge_role == "intent" and source_files:
            # Check if any source file has deprecated signals
            # (We can't check harvest output here, so we check if the source_files
            #  include paths matching known deprecated patterns)
            for sf in source_files:
                if "deprecated" in sf.lower() or "legacy" in sf.lower():
                    findings.append({
                        "id": f"DRF-PRV-{len(findings)+1:03d}",
                        "check": "provenance-consistency",
                        "severity": "DRIFT",
                        "rule": "intent-references-deprecated-source",
                        "node": node_id,
                        "description": f"Intent node references potentially deprecated source file: {sf}",
                    })

    return findings


# ── Check 4: Intent-Observed Consistency ─────────────────────────────

def check_intent_observed_consistency(kb_dir: Path, nodes: List[Dict]) -> List[Dict]:
    findings = []
    for node in nodes:
        knowledge_role = node.get("knowledge_role", "")
        node_id = node.get("id", "unknown")
        page_path = node.get("page_path", "")

        if not page_path:
            continue

        full_path = resolve_page_path(kb_dir, page_path)
        if not full_path:
            continue

        body = load_md(full_path)

        # Rule: intent pages should not have Runtime Path or Source Evidence sections
        if knowledge_role == "intent":
            if has_section(body, "Runtime Path") or has_section(body, "Source Evidence"):
                # Check if it also has disclaimers that make this mixed
                has_disclaimer = any(phrase in body.lower() for phrase in [
                    "in progress", "not yet integrated", "tracked in",
                    "llm-driven", "default path is"
                ])
                if has_disclaimer:
                    findings.append({
                        "id": f"DRF-INT-{len(findings)+1:03d}",
                        "check": "intent-observed-consistency",
                        "severity": "DRIFT",
                        "rule": "intent-observed-mismatch",
                        "node": node_id,
                        "description": f"Intent node '{node_id}' contains observed sections (Runtime Path/Source Evidence) but also contains progress disclaimers — intended vs observed are flattened into one page",
                    })
                else:
                    findings.append({
                        "id": f"REV-INT-{len(findings)+1:03d}",
                        "check": "intent-observed-consistency",
                        "severity": "REVIEW",
                        "rule": "intent-with-observed-sections",
                        "node": node_id,
                        "description": f"Intent node '{node_id}' contains sections normally found in observed pages. Consider knowledge_role=mixed.",
                    })

        # Rule: detect structured step table + progress disclaimer on same page
        if knowledge_role in ("intent", "mixed"):
            has_step_table = bool(re.search(r"\| # \| Description \|", body))
            status_notes = extract_section(body, "Status Notes")
            has_progress_disclaimer = status_notes is not None and any(
                phrase in (status_notes or "").lower()
                for phrase in ["in progress", "not yet", "tracked in", "llm-driven", "default"]
            )
            if has_step_table and has_progress_disclaimer:
                # Check if we already added a DRIFT finding for this node
                if not any(f["node"] == node_id and f["severity"] == "DRIFT" for f in findings):
                    findings.append({
                        "id": f"DRF-INT-{len(findings)+1:03d}",
                        "check": "intent-observed-consistency",
                        "severity": "DRIFT",
                        "rule": "intent-observed-mismatch",
                        "node": node_id,
                        "description": f"Node '{node_id}' has deterministic step table but Status Notes indicates the path is still LLM-driven — contradiction within same page",
                    })

    return findings


# ── Check 5: Canonical Authority / Projection Integrity ───────────────

def check_canonical_authority(kb_dir: Path, nodes: List[Dict], project_root: Path) -> List[Dict]:
    findings = []
    registry = build_canonical_registry(project_root)

    for node in nodes:
        knowledge_role = node.get("knowledge_role", "")
        node_id = node.get("id", "unknown")
        page_path = node.get("page_path", "")
        canonical_source = node.get("canonical_source", None)

        if not page_path:
            continue

        full_path = resolve_page_path(kb_dir, page_path)
        if not full_path:
            continue

        body = load_md(full_path)
        fm, _ = parse_frontmatter(body)

        # Rule: canonical_source set but knowledge_role is not reference or mixed
        if canonical_source:
            cs_path = canonical_source if isinstance(canonical_source, str) else canonical_source.get("path", "")
            cs_anchor = None if isinstance(canonical_source, str) else canonical_source.get("anchor", "")

            if knowledge_role not in ("reference", "mixed"):
                findings.append({
                    "id": f"REV-CAN-{len(findings)+1:03d}",
                    "check": "canonical-authority",
                    "severity": "REVIEW",
                    "rule": "canonical-source-wrong-role",
                    "node": node_id,
                    "description": f"Node has canonical_source='{cs_path}' but knowledge_role='{knowledge_role}'. Should be 'reference' or 'mixed'.",
                })

            # Rule: canonical_source.path must exist
            if cs_path:
                cs_full = project_root / cs_path
                if not cs_full.exists():
                    findings.append({
                        "id": f"ERR-CAN-{len(findings)+1:03d}",
                        "check": "canonical-authority",
                        "severity": "ERROR",
                        "rule": "invalid-canonical-source",
                        "node": node_id,
                        "description": f"canonical_source.path '{cs_path}' does not exist",
                    })
                elif cs_anchor:
                    # Rule: canonical_source.anchor must exist as a heading in the target file
                    try:
                        cs_body = load_md(cs_full)
                    except OSError:
                        findings.append({
                            "id": f"ERR-CAN-{len(findings)+1:03d}",
                            "check": "canonical-authority",
                            "severity": "ERROR",
                            "rule": "invalid-canonical-source",
                            "node": node_id,
                            "description": f"canonical_source.path '{cs_path}' cannot be read",
                        })
                        continue
                    anchor_re = re.compile(
                        rf"^#+\s+{re.escape(cs_anchor)}\s*$", re.MULTILINE
                    )
                    if not anchor_re.search(cs_body):
                        findings.append({
                            "id": f"ERR-CAN-{len(findings)+1:03d}",
                            "check": "canonical-authority",
                            "severity": "ERROR",
                            "rule": "invalid-canonical-source",
                            "node": node_id,
                            "description": f"canonical_source.anchor '{cs_anchor}' not found in '{cs_path}'",
                        })

            # Rule: page with canonical_source should not have How It Works section
            # with redefined contracts (enum tables matching canonical source)
            if has_section(body, "How It Works") or has_section(body, "Specification"):
                # Check if the canonical source has matching enum sections
                for cs_reg_path, cs_info in registry.items():
                    if cs_path and (cs_path == cs_reg_path or cs_path.endswith(cs_reg_path.split("/")[-1])):
                        for enum_sec in cs_info.get("enum_sections", []):
                            page_enums = extract_enum_values(extract_section(body, "How It Works") or body)
                            cs_body = load_md(project_root / cs_reg_path)
                            cs_enums = extract_enum_values(extract_section(cs_body, enum_sec) or cs_body)
                            if page_enums and cs_enums:
                                overlap = set(page_enums) & set(cs_enums)
                                if len(overlap) >= 3:
                                    findings.append({
                                        "id": f"ERR-CAN-{len(findings)+1:03d}",
                                        "check": "canonical-authority",
                                        "severity": "ERROR",
                                        "rule": "canonical-duplication",
                                        "node": node_id,
                                        "description": f"Node with canonical_source still redefines enums from '{cs_reg_path}#{enum_sec}' (overlap: {sorted(overlap)})",
                                    })
                                    break
            continue  # skip further checks for pages that already declare canonical_source

        # Rule: intent page without canonical_source that duplicates canonical content
        if knowledge_role == "intent":
            for cs_path, cs_info in registry.items():
                cs_full = project_root / cs_path
                if not cs_full.exists():
                    continue

                cs_body = load_md(cs_full)

                for enum_sec in cs_info.get("enum_sections", []):
                    cs_section = extract_section(cs_body, enum_sec)
                    if not cs_section:
                        continue
                    cs_enums = set(extract_enum_values(cs_section))
                    if len(cs_enums) < 3:
                        continue

                    # Check page body for matching enums
                    page_enums = set(extract_enum_values(body))
                    overlap = cs_enums & page_enums

                    if len(overlap) >= 3:
                        page_has_matching_section = has_section(body, enum_sec)

                        if page_has_matching_section or len(overlap) >= len(cs_enums) * 0.7:
                            findings.append({
                                "id": f"ERR-CAN-{len(findings)+1:03d}",
                                "check": "canonical-authority",
                                "severity": "ERROR",
                                "rule": "canonical-duplication",
                                "node": node_id,
                                "description": f"Intent node '{node_id}' duplicates enums from canonical source '{cs_path}#{enum_sec}' without declaring canonical_source. Overlap: {sorted(overlap)}",
                            })
                            break

                if any(f["node"] == node_id for f in findings):
                    break

    return findings


# ── Check 6: Report Consistency ───────────────────────────────────────

def check_report_consistency(kb_dir: Path, all_findings: List[Dict]) -> List[Dict]:
    """Post-render invariant: rendered reports must match validation findings.

    Checks both text markers AND actual item counts. If rendered count ≠
    validation count, the report is stale/inconsistent."""
    findings = []
    reports_dir = kb_dir / "reports"

    drift_findings = [f for f in all_findings if f["severity"] == "DRIFT"]
    review_findings = [f for f in all_findings if f["severity"] == "REVIEW"]
    error_findings = [f for f in all_findings if f["severity"] == "ERROR"]

    # Check drift.md
    drift_md = reports_dir / "drift.md"
    if drift_md.exists():
        body = load_md(drift_md)
        # Count actual drift items listed in the report (format: "- **DRF-XXX-NNN** ...")
        report_drift_count = len(re.findall(r"\*\*DRF-[A-Z]+-\d+\*\*", body))
        has_none_text = "No drift detected" in body
        if has_none_text and len(drift_findings) > 0:
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "drift.md",
                "description": f"drift.md claims no drift but validation found {len(drift_findings)} DRIFT items",
            })
        elif not has_none_text and report_drift_count != len(drift_findings):
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "drift.md",
                "description": f"drift.md lists {report_drift_count} items but validation found {len(drift_findings)}",
            })

    # Check needs-review.md
    review_md = reports_dir / "needs-review.md"
    if review_md.exists():
        body = load_md(review_md)
        report_review_count = len(re.findall(r"\*\*REV-[A-Z]+-\d+\*\*", body))
        has_none_text = "No items need review" in body
        if has_none_text and len(review_findings) > 0:
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "needs-review.md",
                "description": f"needs-review.md claims no items but validation found {len(review_findings)} REVIEW items",
            })
        elif not has_none_text and report_review_count != len(review_findings):
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "needs-review.md",
                "description": f"needs-review.md lists {report_review_count} items but validation found {len(review_findings)}",
            })

    return findings


# ── Report Rendering ──────────────────────────────────────────────────

def render_reports_from_findings(findings: List[Dict]) -> Dict[str, str]:
    """Generate report markdown files from validation findings.
    Pure projection — reports are derived from validation state, never authored independently."""
    reports: Dict[str, str] = {}

    # drift.md
    drift_items = [f for f in findings if f["severity"] == "DRIFT"]
    if drift_items:
        lines = ["# Drift Report", "", f"**{len(drift_items)} drift item(s) detected.**", ""]
        for item in drift_items:
            lines.append(f"- **{item['id']}** [{item['check']}/{item.get('rule', '')}] {item.get('node', '')}: {item['description']}")
        lines.append("")
        reports["drift.md"] = "\n".join(lines)
    else:
        reports["drift.md"] = "# Drift Report\n\nNo drift detected.\n"

    # needs-review.md
    review_items = [f for f in findings if f["severity"] == "REVIEW"]
    if review_items:
        lines = ["# Needs Review", "", f"**{len(review_items)} item(s) need review.**", ""]
        for item in review_items:
            lines.append(f"- **{item['id']}** [{item['check']}/{item.get('rule', '')}] {item.get('node', '')}: {item['description']}")
        lines.append("")
        reports["needs-review.md"] = "\n".join(lines)
    else:
        reports["needs-review.md"] = "# Needs Review\n\nNo items need review at this time.\n"

    # knowledge-gaps.md
    gap_findings = [
        f for f in findings
        if f.get("rule", "").endswith("-missing")
        or f["check"] == "required-artifact-integrity"
        or any(word in f.get("description", "").lower() for word in ["unknown", "missing", "gap"])
    ]
    if gap_findings:
        lines = ["# Knowledge Gaps", "", f"**{len(gap_findings)} gap(s) detected.**", ""]
        for item in gap_findings:
            lines.append(f"- **{item['id']}** [{item['check']}/{item.get('rule', '')}] {item.get('node', '')}: {item['description']}")
        lines.append("")
        reports["knowledge-gaps.md"] = "\n".join(lines)
    else:
        reports["knowledge-gaps.md"] = "# Knowledge Gaps\n\nNo knowledge gaps detected.\n"

    return reports


# ── Main ──────────────────────────────────────────────────────────────

def compute_completion_state(findings: List[Dict]) -> str:
    errors = [f for f in findings if f["severity"] == "ERROR"]
    drifts = [f for f in findings if f["severity"] == "DRIFT"]
    reviews = [f for f in findings if f["severity"] == "REVIEW"]

    if errors:
        return "blocked"
    if drifts:
        return "complete_with_drift"
    if reviews:
        return "needs_review"
    return "complete"


def run_validation(kb_dir: Path, project_root: Path) -> Dict:
    graph_dir = kb_dir / "graph"

    # Load graph
    nodes = load_json(graph_dir / "nodes.json") if (graph_dir / "nodes.json").exists() else []
    edges = load_json(graph_dir / "edges.json") if (graph_dir / "edges.json").exists() else []
    diagnostics = load_json(graph_dir / "diagnostics.json") if (graph_dir / "diagnostics.json").exists() else []

    nodes_map = {n.get("id", ""): n for n in nodes}

    # Run checks 1-5 (canonical input validation)
    all_findings: List[Dict] = []
    check_counts: Dict[str, int] = {}

    ref_findings = check_referential_integrity(kb_dir, diagnostics, nodes_map)
    all_findings.extend(ref_findings)
    check_counts["referential-integrity"] = len(diagnostics)

    art_findings = check_required_artifacts(kb_dir, nodes)
    all_findings.extend(art_findings)
    domain_count = len(list((kb_dir / "domains").iterdir())) if (kb_dir / "domains").exists() else 0
    check_counts["required-artifact-integrity"] = 1 + domain_count + 4

    prv_findings = check_provenance_consistency(kb_dir, nodes)
    all_findings.extend(prv_findings)
    check_counts["provenance-consistency"] = len(nodes)

    int_findings = check_intent_observed_consistency(kb_dir, nodes)
    all_findings.extend(int_findings)
    check_counts["intent-observed-consistency"] = len([n for n in nodes if n.get("page_path")])

    can_findings = check_canonical_authority(kb_dir, nodes, project_root)
    all_findings.extend(can_findings)
    check_counts["canonical-authority"] = len([n for n in nodes if n.get("page_path")])

    # Render reports from validation findings BEFORE report consistency check.
    # Reports are derived views — stale derived artifacts must not block validation.
    # The renderer rebuilds them; the postcondition verifies they match.
    reports_dir = kb_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    reports = render_reports_from_findings(all_findings)
    for filename, content in reports.items():
        (reports_dir / filename).write_text(content, encoding="utf-8")

    # Check 6: Report consistency — post-render invariant.
    # Rendered reports must match validation findings.
    rpt_findings = check_report_consistency(kb_dir, all_findings)
    all_findings.extend(rpt_findings)
    check_counts["report-consistency"] = 5

    # Assign sequential IDs
    for i, f in enumerate(all_findings):
        if "id" not in f:
            f["id"] = f"{f['severity'][:3]}-{i+1:03d}"

    # Compute summary
    error_count = len([f for f in all_findings if f["severity"] == "ERROR"])
    drift_count = len([f for f in all_findings if f["severity"] == "DRIFT"])
    review_count = len([f for f in all_findings if f["severity"] == "REVIEW"])
    completion_state = compute_completion_state(all_findings)

    # Build checks_run with actual counts
    checks_run = {}
    for check_name in ["referential-integrity", "required-artifact-integrity",
                        "provenance-consistency", "intent-observed-consistency",
                        "canonical-authority", "report-consistency"]:
        check_findings = [f for f in all_findings if f["check"] == check_name]
        total = check_counts.get(check_name, 0)
        checks_run[check_name] = {
            "total": total,
            "passed": total - len(check_findings),
            "failed": len(check_findings),
        }

    # Deterministic result (same KB → same result)
    deterministic = {
        "completion_state": completion_state,
        "summary": {
            "total_findings": len(all_findings),
            "error_count": error_count,
            "drift_count": drift_count,
            "review_count": review_count,
        },
        "findings": all_findings,
        "checks_run": checks_run,
    }

    # Non-deterministic metadata (separate from deterministic result)
    try:
        rel_path = str(kb_dir.relative_to(project_root))
    except ValueError:
        rel_path = str(kb_dir)
    run_metadata = {
        "kb_path": rel_path,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {**deterministic, **run_metadata}


def main():
    parser = argparse.ArgumentParser(description="Kode Brain Onboard Validation Gate")
    parser.add_argument("kb_dir", help="Path to KB directory (e.g. docs/brain/projects/kodebrain/)")
    parser.add_argument("--project-root", default=".", help="Project root for resolving canonical sources")
    parser.add_argument("--output", "-o", help="Output path for validation-result.json (default: kb_dir/graph/validation-result.json)")
    parser.add_argument("--render", action="store_true", help="Render reports from validation findings")
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    project_root = Path(args.project_root).resolve()

    if not kb_dir.exists():
        print(f"Error: KB directory not found: {kb_dir}", file=sys.stderr)
        sys.exit(1)

    result = run_validation(kb_dir, project_root)

    output_path = Path(args.output) if args.output else kb_dir / "graph" / "validation-result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    # Reports are rendered during run_validation() — post-render consistency
    # is checked as Check 6. The --render flag is accepted for backward
    # compatibility but is now a no-op (always rendered).
    if args.render:
        reports_dir = kb_dir / "reports"
        print(f"Reports written to: {reports_dir}")

    cs = result["completion_state"]
    s = result["summary"]
    print(f"Validation complete: {cs}")
    print(f"  ERROR:  {s['error_count']}")
    print(f"  DRIFT:  {s['drift_count']}")
    print(f"  REVIEW: {s['review_count']}")
    print(f"  Total:  {s['total_findings']}")
    print(f"Output: {output_path}")

    sys.exit(0 if cs != "blocked" else 1)


if __name__ == "__main__":
    main()
