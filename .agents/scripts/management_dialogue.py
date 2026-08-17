"""Coordinate file-based turns between multiple interactive model sessions.

This helper does not call model APIs or inject text into GUI windows. It keeps
the shared dialogue state, creates the next-turn instruction file, and records
which model produced each review/response artifact.

Typical use:
    python .agents/scripts/management_dialogue.py init \
        --topic M2_EXECUTIVE_ARCHITECTURE \
        --plan management/M2_EXECUTIVE_ARCHITECTURE_IMPLEMENTATION_PLAN.md \
        --agents CODEX GEMINI
    python .agents/scripts/management_dialogue.py next --topic M2_EXECUTIVE_ARCHITECTURE
    python .agents/scripts/management_dialogue.py complete-turn \
        --topic M2_EXECUTIVE_ARCHITECTURE --agent CODEX \
        --artifact management/responses/<file>.md --kind response \
        --validation "focused tests: passed"
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MANAGEMENT_ROOT = REPO_ROOT / "management"
DIALOGUE_ROOT = MANAGEMENT_ROOT / "dialogue"
STATE_VERSION = 2
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class DialogueError(Exception):
    """An expected command or state error."""


def today() -> str:
    return dt.date.today().isoformat()


def validate_name(value: str, label: str) -> str:
    if not SAFE_NAME.fullmatch(value):
        raise DialogueError(
            f"Invalid {label} '{value}'. Use letters, numbers, '_' or '-'."
        )
    return value


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise DialogueError(f"Path must be inside the repository: {path}") from exc


def resolve_repo_path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        candidate.resolve().relative_to(REPO_ROOT)
    except ValueError as exc:
        raise DialogueError(f"Path must be inside the repository: {value}") from exc
    return candidate.resolve()


def state_path(topic: str) -> Path:
    validate_name(topic, "topic")
    return DIALOGUE_ROOT / f"{topic}_state.json"


def load_state(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    path = resolve_repo_path(args.state) if getattr(args, "state", None) else state_path(args.topic)
    if not path.exists():
        raise DialogueError(f"Dialogue state not found: {repo_relative(path)}")
    try:
        state = upgrade_state(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise DialogueError(f"Invalid JSON state file: {repo_relative(path)}") from exc
    plan = resolve_repo_path(state["canonical_plan"])
    if plan.exists() and not state.get("plan_revision"):
        state["plan_revision"] = file_hash(plan)
        save_state(state, path)
    return state, path


def save_state(state: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decisions_path(state: dict[str, Any]) -> Path:
    return DIALOGUE_ROOT / f"{state['topic']}_decisions.json"


def upgrade_state(state: dict[str, Any]) -> dict[str, Any]:
    """Add v2 audit fields without invalidating an existing dialogue."""
    if state.get("schema_version") not in (1, STATE_VERSION):
        raise DialogueError("Unsupported dialogue state schema")
    state.setdefault("phase", "design")
    state.setdefault("acceptance_criteria", [])
    state.setdefault("unresolved_items", [])
    state.setdefault("decisions", [])
    state.setdefault("verification", [])
    state.setdefault("close_reason", None)
    state.setdefault("plan_revision", None)
    state.setdefault("validation_evidence", [])
    state["schema_version"] = STATE_VERSION
    return state


def command_init(args: argparse.Namespace) -> int:
    topic = validate_name(args.topic, "topic")
    agents = [validate_name(agent.upper(), "agent") for agent in args.agents]
    if len(agents) < 2:
        raise DialogueError("At least two agents are required.")
    if len(set(agents)) != len(agents):
        raise DialogueError("Agent labels must be unique.")

    plan = resolve_repo_path(args.plan)
    if not plan.exists():
        raise DialogueError(f"Canonical plan not found: {repo_relative(plan)}")

    path = state_path(topic)
    if path.exists() and not args.force:
        raise DialogueError(
            f"State already exists: {repo_relative(path)}. Use --force only to start over."
        )

    DIALOGUE_ROOT.mkdir(parents=True, exist_ok=True)
    (MANAGEMENT_ROOT / "reviews").mkdir(exist_ok=True)
    (MANAGEMENT_ROOT / "responses").mkdir(exist_ok=True)
    state = {
        "schema_version": STATE_VERSION,
        "topic": topic,
        "canonical_plan": repo_relative(plan),
        "agents": agents,
        "phase": args.phase,
        "acceptance_criteria": args.acceptance_criteria,
        "round": 1,
        "turn": 0,
        "status": "ready_for_agent",
        "next_agent": agents[0],
        "last_agent": None,
        "latest_artifact": None,
        "latest_artifact_kind": None,
        "next_turn_file": None,
        "history": [],
        "user_decision": None,
        "decisions": [],
        "unresolved_items": [],
        "verification": [],
        "close_reason": None,
        "plan_revision": file_hash(plan),
        "created": today(),
        "updated": today(),
    }
    save_state(state, path)
    decisions_path(state).write_text("[]\n", encoding="utf-8")
    print(f"Initialized {repo_relative(path)}")
    print(f"Next agent: {agents[0]}")
    return 0


def next_turn_path(state: dict[str, Any]) -> Path:
    return DIALOGUE_ROOT / f"{state['topic']}_NEXT_TURN.md"


def command_next(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    if state["status"] == "closed":
        raise DialogueError("Dialogue is closed.")
    requested = args.agent.upper() if args.agent else state["next_agent"]
    if requested not in state["agents"]:
        raise DialogueError(f"Unknown agent '{requested}'. Use one of {state['agents']}.")
    if state["status"] == "waiting_for_agent" and requested == state["next_agent"]:
        turn_file = resolve_repo_path(state["next_turn_file"])
        print(f"Turn already prepared: {repo_relative(turn_file)}")
        print(f"Open {requested} and ask it to read that file.")
        return 0
    if state["status"] == "waiting_for_user":
        raise DialogueError("Dialogue is waiting for a user decision before another turn.")

    latest = state.get("latest_artifact") or "(none — this is the initial plan review)"
    plan = resolve_repo_path(state["canonical_plan"])
    state["plan_revision"] = file_hash(plan)
    criteria = "\n".join(f"- {item}" for item in state.get("acceptance_criteria", [])) or "- None recorded"
    unresolved = "\n".join(f"- {item}" for item in state.get("unresolved_items", [])) or "- None recorded"
    decisions = "\n".join(
        f"- {item['id']}: {item['status']} — {item['question']}"
        for item in state.get("decisions", [])
    ) or "- None recorded"
    turn_file = next_turn_path(state)
    prompt = f"""# Next dialogue turn: {state['topic']}

You are **{requested}**, taking round {state['round']} turn {state['turn'] + 1}.
Phase: **{state['phase']}**
Canonical plan revision: `{state['plan_revision']}`

Read these files from the repository:

- `{state['canonical_plan']}` — canonical plan;
- `{latest}` — latest review/response artifact, if present;
- `{repo_relative(path)}` — dialogue state;
- `.agents/skills/management-plan-dialogue/SKILL.md` — turn protocol.

Acceptance criteria:
{criteria}

Unresolved items:
{unresolved}

Decision register:
{decisions}

Make an independent judgment. Do not blindly accept the previous model's
recommendations. Identify corrections, disagreements, open questions, and your
own new ideas. Save a substantial review under `management/reviews/` or a
response under `management/responses/`. If this turn is authorized to update
the plan, update the canonical plan and preserve the discussion links.

When finished, save a completion/review artifact and include changed files and
exact validation evidence, then record it with:

```powershell
python .agents\\scripts\\management_dialogue.py complete-turn --topic {state['topic']} --agent {requested} --artifact <repo-relative-file> --kind <review|response|plan> --changed-file <repo-relative-file> --validation "<command>: <result>"
```

Use `--unresolved <item>` for any question that remains open.

Do not put real business data in this public repository.
"""
    turn_file.write_text(prompt, encoding="utf-8")
    state["status"] = "waiting_for_agent"
    state["next_agent"] = requested
    state["next_turn_file"] = repo_relative(turn_file)
    state["updated"] = today()
    save_state(state, path)
    print(f"Next turn prepared for {requested}: {repo_relative(turn_file)}")
    print(f"Switch to {requested} and ask it to read {repo_relative(turn_file)}.")
    return 0


def command_complete(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    agent = validate_name(args.agent.upper(), "agent")
    if agent != state["next_agent"]:
        raise DialogueError(f"Expected {state['next_agent']} to complete this turn, not {agent}.")
    artifact = resolve_repo_path(args.artifact)
    if not artifact.exists() or not artifact.is_file():
        raise DialogueError(f"Artifact not found: {repo_relative(artifact)}")
    if artifact == path or artifact == next_turn_path(state):
        raise DialogueError("The state file and NEXT_TURN.md cannot be submitted as artifacts.")

    next_index = (state["agents"].index(agent) + 1) % len(state["agents"])
    next_agent = state["agents"][next_index]
    state["turn"] += 1
    if next_index == 0:
        state["round"] += 1
    state["last_agent"] = agent
    state["latest_artifact"] = repo_relative(artifact)
    state["latest_artifact_kind"] = args.kind
    state["plan_revision_before"] = state.get("plan_revision")
    state["plan_revision"] = file_hash(resolve_repo_path(state["canonical_plan"]))
    state["changed_files"] = args.changed_file
    state["unresolved_items"] = args.unresolved
    state["validation_evidence"] = args.validation
    state["next_agent"] = next_agent
    state["status"] = "ready_for_agent"
    state["next_turn_file"] = None
    state["updated"] = today()
    state["history"].append(
        {
            "turn": state["turn"],
            "round": state["round"],
            "agent": agent,
            "artifact": repo_relative(artifact),
            "kind": args.kind,
            "date": today(),
            "plan_revision_before": state["plan_revision_before"],
            "plan_revision_after": state["plan_revision"],
            "changed_files": args.changed_file,
            "unresolved_items": args.unresolved,
            "validation_evidence": args.validation,
        }
    )
    save_state(state, path)
    print(f"Recorded turn {state['turn']} from {agent}: {repo_relative(artifact)}")
    print(f"Next agent: {next_agent}. Run the 'next' command to prepare its instruction.")
    return 0


def command_user_input(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    artifact = resolve_repo_path(args.artifact)
    if not artifact.exists() or not artifact.is_file():
        raise DialogueError(f"User decision file not found: {repo_relative(artifact)}")
    state["latest_artifact"] = repo_relative(artifact)
    state["latest_artifact_kind"] = "user_input"
    state["user_decision"] = repo_relative(artifact)
    state["status"] = "ready_for_agent"
    state["updated"] = today()
    save_state(state, path)
    print(f"Recorded user decision: {repo_relative(artifact)}")
    return 0


def command_close(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    state["status"] = "closed"
    state["close_reason"] = args.reason
    state["next_agent"] = None
    state["next_turn_file"] = None
    state["updated"] = today()
    save_state(state, path)
    print(f"Closed dialogue {state['topic']}: {args.reason}")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    state["verification"].append({"result": args.result, "notes": args.notes, "date": today()})
    state["status"] = "verified" if args.result == "pass" else "verification_failed"
    state["updated"] = today()
    save_state(state, path)
    print(f"Recorded verification result: {args.result}")
    return 0


def command_decision(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    item = {
        "id": validate_name(args.id, "decision id"),
        "question": args.question,
        "proposal": args.proposal,
        "status": args.status,
        "decided_by": args.decided_by,
        "source": args.source,
        "affected_files": args.affected_file,
    }
    state["decisions"] = [x for x in state.get("decisions", []) if x["id"] != item["id"]] + [item]
    decisions_path(state).write_text(json.dumps(state["decisions"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    state["updated"] = today()
    save_state(state, path)
    print(f"Recorded decision {item['id']}: {item['status']}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    state, path = load_state(args)
    print(json.dumps({"state_file": repo_relative(path), **state}, indent=2, ensure_ascii=False))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize a dialogue state file")
    init.add_argument("--topic", required=True)
    init.add_argument("--plan", required=True, help="Repository-relative canonical plan path")
    init.add_argument("--agents", nargs="+", required=True, help="Two or more model labels")
    init.add_argument("--phase", default="design", help="Current phase, e.g. design or phase-2")
    init.add_argument("--acceptance-criteria", action="append", default=[])
    init.add_argument("--force", action="store_true", help="Replace an existing state file")

    for name in ("next", "status"):
        command = sub.add_parser(name, help=f"{name.title()} the dialogue")
        command.add_argument("--topic", required=True)
        command.add_argument("--state", help="Optional repository-relative state path")
        if name == "next":
            command.add_argument("--agent", help="Override the next agent")

    complete = sub.add_parser("complete-turn", help="Record a model's completed artifact")
    complete.add_argument("--topic", required=True)
    complete.add_argument("--state", help="Optional repository-relative state path")
    complete.add_argument("--agent", required=True)
    complete.add_argument("--artifact", required=True, help="Repository-relative review/response/plan file")
    complete.add_argument("--kind", choices=("review", "response", "plan"), required=True)
    complete.add_argument("--changed-file", action="append", default=[])
    complete.add_argument("--unresolved", action="append", default=[])
    complete.add_argument("--validation", action="append", default=[])
    user = sub.add_parser("user-input", help="Record a user decision artifact")
    user.add_argument("--topic", required=True); user.add_argument("--state"); user.add_argument("--artifact", required=True)
    close = sub.add_parser("close", help="Close a dialogue")
    close.add_argument("--topic", required=True); close.add_argument("--state"); close.add_argument("--reason", required=True)
    verify = sub.add_parser("verify", help="Record phase verification")
    verify.add_argument("--topic", required=True); verify.add_argument("--state")
    verify.add_argument("--result", choices=("pass", "fail"), required=True); verify.add_argument("--notes", required=True)
    decision = sub.add_parser("decision", help="Add or update a decision-register item")
    decision.add_argument("--topic", required=True); decision.add_argument("--state"); decision.add_argument("--id", required=True)
    decision.add_argument("--question", required=True); decision.add_argument("--proposal", required=True)
    decision.add_argument("--status", choices=("open", "accepted", "rejected", "deferred"), required=True)
    decision.add_argument("--decided-by", default=""); decision.add_argument("--source", default="")
    decision.add_argument("--affected-file", action="append", default=[])
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return {
            "init": command_init,
            "next": command_next,
            "complete-turn": command_complete,
            "user-input": command_user_input,
            "close": command_close,
            "verify": command_verify,
            "decision": command_decision,
            "status": command_status,
        }[args.command](args)
    except DialogueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
