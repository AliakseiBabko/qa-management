"""Mechanical consistency validation for this repo's convention-mirrored files.

The `repo-maintenance` skill lists the mirrors that must stay in sync by
hand (AGENTS.md skill table <-> .agents/skills/, README <-> .agents/scripts/,
document_graph.yaml <-> skills/scripts/aliases, source-type lists in
pipeline_common <-> google-workspace-rules.md). This script is that
checklist automated - the same move as check_cascade_closure.py for the
data-side cascade. Run it before committing any structural change; exit 1
means drift.

Checks (FAIL = exit 1):
- every .agents/skills/<dir> has a SKILL.md whose frontmatter `name`
  matches the directory, and a row in AGENTS.md's skill table; every table
  row points at an existing skill directory and SKILL.md path
- every .agents/scripts/*.py is mentioned in README.md, and every
  `<name>.py` mentioned in README/AGENTS exists
- document_graph.yaml parses; every edge target / alias target / source
  entry is a defined document node; edge kinds are valid; every
  `script:` value exists in .agents/scripts; `periodic` names don't
  collide with document nodes
- every graph `sources:` key is a canonical source_type from
  pipeline_common.SKILL_INVOCATION_SOURCE_TYPES
- every canonical source_type appears (backticked) in
  google-workspace-rules.md
- every `Templates/<file>` referenced in skills/AGENTS/README exists

Warnings (reported, exit 0):
- canonical source_types with no `sources:` route in the graph
- Templates files referenced by nothing

Usage:  python .agents/scripts/validate_repo.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO / ".agents" / "skills"
SCRIPTS_DIR = REPO / ".agents" / "scripts"
GRAPH = REPO / ".agents" / "document_graph.yaml"
RULES = SKILLS_DIR / "qa-management-roles" / "references" / "google-workspace-rules.md"
VALID_KINDS = {"direct", "gated", "judgment", "script"}

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_frontmatter_name(skill_md: Path) -> str | None:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:30]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def check_skills_vs_agents_md() -> None:
    agents_md = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    table_rows = re.findall(r"^\| `([a-z0-9-]+)` \|.*\| `(\.agents/skills/[^`]+)` \|",
                            agents_md, re.MULTILINE)
    table = {name: path for name, path in table_rows}

    dirs = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    for d in sorted(dirs):
        skill_md = SKILLS_DIR / d / "SKILL.md"
        if not skill_md.exists():
            fail(f"skill dir without SKILL.md: .agents/skills/{d}")
            continue
        fm_name = parse_frontmatter_name(skill_md)
        if fm_name != d:
            fail(f"SKILL.md frontmatter name {fm_name!r} != directory name {d!r}")
        if d not in table:
            fail(f"skill {d!r} has no row in AGENTS.md's skill table")
    for name, path in sorted(table.items()):
        if name not in dirs:
            fail(f"AGENTS.md table row {name!r} has no .agents/skills/{name} directory")
        elif not (REPO / path).exists():
            fail(f"AGENTS.md table row {name!r} points at missing path {path}")


def check_scripts_vs_readme() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    agents_md = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    scripts = {p.name for p in SCRIPTS_DIR.glob("*.py")}
    for name in sorted(scripts):
        if name not in readme:
            fail(f"script {name} has no mention in README.md (Current pipeline scripts)")
    mentioned = set(re.findall(r"`?([a-z0-9_]+\.py)`?", readme + agents_md))
    for name in sorted(mentioned):
        if name not in scripts and not (SCRIPTS_DIR / name).exists():
            # skill-local scripts live under .agents/skills/*/scripts too
            if not list(SKILLS_DIR.glob(f"*/**/{name}")) and not list(REPO.glob(f"**/{name}")):
                fail(f"README/AGENTS mention {name} but no such file exists in the repo")


def load_source_types() -> set[str]:
    tree = ast.parse((SCRIPTS_DIR / "pipeline_common.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", "") == "SKILL_INVOCATION_SOURCE_TYPES":
                    return set(ast.literal_eval(node.value))
    fail("SKILL_INVOCATION_SOURCE_TYPES not found in pipeline_common.py")
    return set()


def check_graph(source_types: set[str]) -> None:
    try:
        graph = yaml.safe_load(GRAPH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"document_graph.yaml does not parse: {exc}")
        return
    docs = graph.get("documents") or {}
    periodic = set(graph.get("periodic") or [])
    aliases = graph.get("aliases") or {}
    sources = graph.get("sources") or {}
    scripts = {p.name for p in SCRIPTS_DIR.glob("*.py")}

    for name, node in docs.items():
        for edge in (node or {}).get("downstream") or []:
            target, kind = edge.get("to"), edge.get("kind")
            if target not in docs:
                fail(f"graph edge {name} -> {target}: target is not a defined document node")
            if kind not in VALID_KINDS:
                fail(f"graph edge {name} -> {target}: kind {kind!r} not in {sorted(VALID_KINDS)}")
            if kind == "script" and edge.get("script") not in scripts:
                fail(f"graph edge {name} -> {target}: script {edge.get('script')!r} "
                     "not found in .agents/scripts")
    for alias, target in aliases.items():
        if target not in docs:
            fail(f"graph alias {alias!r} -> {target!r}: target is not a defined document node")
    for p in periodic:
        if p in docs:
            fail(f"graph periodic entry {p!r} collides with a document node")
    def check_route(stype: str, label: str, spec: dict) -> None:
        for doc in (spec or {}).get("entry") or []:
            if doc not in docs:
                fail(f"graph source {stype!r}{label} entry {doc!r} is not a defined document node")
        for skill in (spec or {}).get("skills") or []:
            if not (SKILLS_DIR / skill / "SKILL.md").exists():
                fail(f"graph source {stype!r}{label} names missing skill {skill!r}")

    for stype, spec in sources.items():
        if stype not in source_types:
            fail(f"graph source {stype!r} is not a canonical source_type "
                 f"(pipeline_common.SKILL_INVOCATION_SOURCE_TYPES: {sorted(source_types)})")
        spec = spec or {}
        if "routes" in spec:
            if "entry" in spec or "skills" in spec:
                fail(f"graph source {stype!r} mixes routes: with flat skills/entry - pick one shape")
            for variant, route in (spec["routes"] or {}).items():
                check_route(stype, f" route {variant!r}", route)
        else:
            check_route(stype, "", spec)
    # Types that legitimately have no route: retro edits repo rules, and the
    # pre-classification labels only mark unprocessed intake rows.
    unrouted_ok = {"retro", "raw_transcript", "raw_chat", "source_document"}
    for stype in sorted(source_types - set(sources) - unrouted_ok):
        warn(f"canonical source_type {stype!r} has no sources: route in document_graph.yaml")


def check_source_types_documented(source_types: set[str]) -> None:
    rules = RULES.read_text(encoding="utf-8")
    for stype in sorted(source_types):
        if f"`{stype}`" not in rules:
            fail(f"source_type {stype!r} is in pipeline_common but not documented "
                 "in google-workspace-rules.md's canonical list")


def check_source_type_literals(source_types: set[str]) -> None:
    """Every source_type literal used at runtime (scripts) or instructed
    (skills) must be canonical - this is exactly how `1to1_transcript` and
    the raw intake labels drifted unnoticed."""
    patterns = [
        re.compile(r'source_type\s*=\s*"([a-z_]+)"'),        # python assignment
        re.compile(r'"source_type":\s*"([a-z_]+)"'),          # python dict literal
        re.compile(r'`source_type`\s*=\s*`([a-z_]+)`'),       # markdown instruction
    ]
    files = [p for p in SCRIPTS_DIR.glob("*.py") if p.name != "validate_repo.py"]
    files += list(SKILLS_DIR.glob("*/SKILL.md")) + list(SKILLS_DIR.glob("*/references/*.md"))
    for f in files:
        content = f.read_text(encoding="utf-8")
        for pat in patterns:
            for value in pat.findall(content):
                if value not in source_types:
                    fail(f"{f.relative_to(REPO)}: source_type literal {value!r} is not canonical "
                         f"({sorted(source_types)})")


def check_format_drift() -> None:
    """Development plans are Google Docs (sync_m2_plans_to_docs.py); any
    .gsheet mention of them is documentation drift."""
    for name in ("AGENTS.md", "README.md"):
        content = (REPO / name).read_text(encoding="utf-8")
        for m in re.findall(r"\S*development_plan\.gsheet", content):
            fail(f"{name}: {m} - development plans are Google Docs (.gdoc), not Sheets")


def check_templates() -> None:
    templates = {p.name for p in (REPO / "Templates").iterdir() if p.is_file()}
    referenced: set[str] = set()
    texts = [(REPO / "AGENTS.md"), (REPO / "README.md")]
    texts += list(SKILLS_DIR.glob("*/SKILL.md")) + list(SKILLS_DIR.glob("*/references/*.md"))
    for f in texts:
        content = f.read_text(encoding="utf-8")
        for m in re.findall(r"Templates[/\\]([^\s`\")\]]+)", content):
            referenced.add(m.rstrip(".,;:"))
    for ref in sorted(referenced):
        if ref not in templates:
            fail(f"referenced template Templates/{ref} does not exist")
    for t in sorted(templates - referenced):
        warn(f"Templates/{t} is referenced by no skill/AGENTS/README text")


def main() -> int:
    source_types = load_source_types()
    check_skills_vs_agents_md()
    check_scripts_vs_readme()
    check_graph(source_types)
    check_source_types_documented(source_types)
    check_source_type_literals(source_types)
    check_format_drift()
    check_templates()

    for w in warnings:
        print(f"WARN  {w}")
    for f_ in failures:
        print(f"FAIL  {f_}")
    print(f"\n{len(failures)} failure(s), {len(warnings)} warning(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
