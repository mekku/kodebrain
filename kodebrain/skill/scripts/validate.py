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


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown text.
    Handles simple YAML frontmatter (--- delimited)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    yaml_str = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML parser for known flat + list fields
    fm: Dict[str, Any] = {}
    current_list_key = None
    for line in yaml_str.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item
        if stripped.startswith("- "):
            list_val = stripped[2:].strip().strip('"').strip("'")
            if current_list_key:
                fm.setdefault(current_list_key, []).append(list_val)
            continue

        # Key: value
        if ":" in stripped:
            # End current list context
            current_list_key = None

            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val == "":
                # Could be start of inline list or nested object
                current_list_key = key
                continue
            else:
                fm[key] = val
                current_list_key = None

    return fm, body


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

CANONICAL_REGISTRY = {
    "docs/design/spec/knowledge-model.md": {
        "owns": [
            "knowledge.layers", "provenance", "confidence", "knowledge_role",
            "drift", "harvest-policy", "graph-compilation"
        ],
        "enum_sections": [],  # no lifecycle enums in this spec
    },
    "docs/design/spec/project-model.md": {
        "owns": [
            "project.structure", "project.layout", "node-id-format",
            "domain-contract", "architecture-contract", "project-hub-contract"
        ],
        "enum_sections": [],
    },
    "docs/design/spec/workflow-model.md": {
        "owns": [
            "onboarding.process", "change-lifecycle", "change-record-structure",
            "status-lifecycle-separation", "agent.behavior"
        ],
        "enum_sections": ["Change Lifecycle States"],
    },
    "docs/design/spec/history-model.md": {
        "owns": [
            "decision-lifecycle", "decision-lineage", "incident-lifecycle",
            "incident-record", "milestone-record", "temporal-records"
        ],
        "enum_sections": ["Decision Lifecycle", "Incident Lifecycle"],
    },
    "docs/design/spec/governance.md": {
        "owns": [
            "spec-authority", "precedence", "compatibility",
            "non-goals", "success-criteria"
        ],
        "enum_sections": [],
    },
}


# ── Check 1: Referential Integrity ───────────────────────────────────

def check_referential_integrity(kb_dir: Path, edges: List[Dict], nodes_map: Dict[str, Any]) -> List[Dict]:
    findings = []
    for edge in edges:
        target = edge.get("to", edge.get("target", ""))
        source = edge.get("from", edge.get("source", ""))
        edge_type = edge.get("type", "")

        # Check if target page exists
        target_path = resolve_node_path(kb_dir, target)
        if target_path and target_path.exists():
            continue

        # Classify severity
        severity = "ERROR" if is_required_reference(edge_type, source, nodes_map) else "REVIEW"

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


def resolve_node_path(kb_dir: Path, node_id: str) -> Optional[Path]:
    """Try to resolve a node ID to a file path."""
    # Try domain-based paths
    parts = node_id.split("-", 1)

    # Direct file path (e.g. changes/active/2026-08-07-vnext-substrate)
    direct = kb_dir / f"{node_id}.md"
    if direct.exists():
        return direct

    # Domain-based paths
    for domain_dir in (kb_dir / "domains").iterdir() if (kb_dir / "domains").exists() else []:
        if not domain_dir.is_dir():
            continue
        for subdir in ["capabilities", "flows", "concepts", "models", "risks", "decisions"]:
            candidate = domain_dir / subdir / f"{node_id}.md"
            if candidate.exists():
                return candidate
        # Domain hub itself
        domain_name = domain_dir.name
        if node_id == domain_name:
            hub = domain_dir / f"{domain_name}.md"
            if hub.exists():
                return hub

    # Project hub
    hub = kb_dir / f"{node_id}.md"
    if hub.exists():
        return hub

    # Changes directory
    if "changes/" in node_id:
        candidate = kb_dir / f"{node_id}.md"
        if candidate.exists():
            return candidate

    return None


def is_required_reference(edge_type: str, source: str, nodes_map: Dict) -> bool:
    """Determine if a reference is required (missing = ERROR) vs optional (missing = REVIEW)."""
    # Active Changes section → required
    if edge_type in ("references",) and source.endswith("kodebrain"):
        # Check if the edge came from Active Changes section
        return True

    # Domain dependency → required
    if edge_type == "depends_on":
        return True

    # Risk reference from a domain → required
    if edge_type == "has_caveat":
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
            has_progress_disclaimer = has_subsection(body, "Status Notes", "") and any(
                phrase in (extract_section(body, "Status Notes") or "").lower()
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

            # Rule: page with canonical_source should not have How It Works section
            # with redefined contracts (enum tables matching canonical source)
            if has_section(body, "How It Works") or has_section(body, "Specification"):
                # Check if the canonical source has matching enum sections
                for cs_reg_path, cs_info in CANONICAL_REGISTRY.items():
                    if cs_path and cs_path.startswith(cs_reg_path) or (cs_reg_path.endswith(cs_path.split("/")[-1]) if cs_path else False):
                        for enum_sec in cs_info.get("enum_sections", []):
                            # Check if this page also has matching section
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
            # For each canonical source, check if this page duplicates its enums
            for cs_path, cs_info in CANONICAL_REGISTRY.items():
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
                        # Check if page has same section heading
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
    findings = []
    reports_dir = kb_dir / "reports"

    drift_findings = [f for f in all_findings if f["severity"] == "DRIFT"]
    review_findings = [f for f in all_findings if f["severity"] == "REVIEW"]
    error_findings = [f for f in all_findings if f["severity"] == "ERROR"]

    # Check drift.md
    drift_md = reports_dir / "drift.md"
    if drift_md.exists():
        body = load_md(drift_md)
        if "None detected" in body and len(drift_findings) > 0:
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "drift.md",
                "description": f"drift.md claims 'None detected' but validation found {len(drift_findings)} DRIFT items",
            })

    # Check needs-review.md
    review_md = reports_dir / "needs-review.md"
    if review_md.exists():
        body = load_md(review_md)
        if "None at this time" in body and len(review_findings) > 0:
            findings.append({
                "id": f"ERR-RPT-{len(findings)+1:03d}",
                "check": "report-consistency",
                "severity": "ERROR",
                "rule": "report-contradicts-validation",
                "report": "needs-review.md",
                "description": f"needs-review.md claims no items but validation found {len(review_findings)} REVIEW items",
            })

    return findings


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

    nodes_map = {n.get("id", ""): n for n in nodes}

    # Run checks
    all_findings: List[Dict] = []

    ref_findings = check_referential_integrity(kb_dir, edges, nodes_map)
    all_findings.extend(ref_findings)

    art_findings = check_required_artifacts(kb_dir, nodes)
    all_findings.extend(art_findings)

    prv_findings = check_provenance_consistency(kb_dir, nodes)
    all_findings.extend(prv_findings)

    int_findings = check_intent_observed_consistency(kb_dir, nodes)
    all_findings.extend(int_findings)

    can_findings = check_canonical_authority(kb_dir, nodes, project_root)
    all_findings.extend(can_findings)

    rpt_findings = check_report_consistency(kb_dir, all_findings)
    all_findings.extend(rpt_findings)

    # Assign sequential IDs
    for i, f in enumerate(all_findings):
        if "id" not in f:
            f["id"] = f"{f['severity'][:3]}-{i+1:03d}"

    # Compute summary
    error_count = len([f for f in all_findings if f["severity"] == "ERROR"])
    drift_count = len([f for f in all_findings if f["severity"] == "DRIFT"])
    review_count = len([f for f in all_findings if f["severity"] == "REVIEW"])
    completion_state = compute_completion_state(all_findings)

    # Build checks_run
    checks_run = {}
    for check_name in ["referential-integrity", "required-artifact-integrity",
                        "provenance-consistency", "intent-observed-consistency",
                        "canonical-authority", "report-consistency"]:
        check_findings = [f for f in all_findings if f["check"] == check_name]
        total = 0
        if check_name == "referential-integrity":
            total = len(edges)
        elif check_name == "required-artifact-integrity":
            total = 10  # approximate
        elif check_name == "provenance-consistency":
            total = len(nodes)
        elif check_name == "intent-observed-consistency":
            total = len(nodes)
        elif check_name == "canonical-authority":
            total = len(nodes)
        elif check_name == "report-consistency":
            total = 5
        checks_run[check_name] = {
            "total": total,
            "passed": total - len(check_findings),
            "failed": len(check_findings),
        }

    return {
        "kb_path": str(kb_dir),
        "validated_at": datetime.now(timezone.utc).isoformat(),
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


def main():
    parser = argparse.ArgumentParser(description="Kode Brain Onboard Validation Gate")
    parser.add_argument("kb_dir", help="Path to KB directory (e.g. docs/brain/projects/kodebrain/)")
    parser.add_argument("--project-root", default=".", help="Project root for resolving canonical sources")
    parser.add_argument("--output", "-o", help="Output path for validation-result.json (default: kb_dir/graph/validation-result.json)")
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
