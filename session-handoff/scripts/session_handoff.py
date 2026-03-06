#!/usr/bin/env python3
"""Generate a cross-agent handoff packet from a Claude, Codex, or Kimi session ID."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

HOME = Path.home()
CLAUDE_ROOT = HOME / ".claude"
CODEX_ROOT = HOME / ".codex"
KIMI_ROOT = HOME / ".kimi"


@dataclass
class Message:
    role: str
    text: str
    timestamp: Optional[str] = None


@dataclass
class SessionData:
    provider: str
    session_id: str
    source_file: Path
    cwd: Optional[str]
    branch: Optional[str]
    started_at: Optional[str]
    messages: list[Message]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a context handoff packet from a Claude or Codex session ID.",
    )
    parser.add_argument("session_id", help="Session ID to resume")
    parser.add_argument(
        "--provider",
        choices=["auto", "claude", "codex", "kimi"],
        default="auto",
        help="Force provider or auto-detect (default: auto)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=16,
        help="Number of recent conversation messages to include",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include the full captured conversation instead of only the latest messages",
    )
    parser.add_argument("-o", "--output", help="Write packet to file instead of stdout")
    return parser.parse_args()


def _safe_json(line: str) -> Optional[dict[str, Any]]:
    try:
        return json.loads(line)
    except Exception:
        return None


def _normalize(text: str, max_len: int = 1400) -> str:
    compact = " ".join((text or "").strip().split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def _is_noise(text: str) -> bool:
    patterns = (
        "# AGENTS.md instructions",
        "<environment_context>",
        "<INSTRUCTIONS>",
        "<turn_aborted>",
        "<permissions instructions>",
        "<app-context>",
        "<collaboration_mode>",
    )
    lowered = text.lower()
    return any(p.lower() in lowered for p in patterns)


def _extract_claude_text(message_obj: dict[str, Any]) -> str:
    content = message_obj.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for chunk in content:
            if not isinstance(chunk, dict):
                continue
            ctype = chunk.get("type")
            if ctype == "text" and isinstance(chunk.get("text"), str):
                chunks.append(chunk["text"])
            elif ctype == "tool_result":
                c = chunk.get("content")
                if isinstance(c, str):
                    chunks.append(c)
        return "\n".join(chunks)

    return ""


def _find_claude_session_file(session_id: str) -> Optional[Path]:
    projects = CLAUDE_ROOT / "projects"
    if not projects.exists():
        return None

    matches = list(projects.glob(f"**/{session_id}.jsonl"))
    return matches[0] if matches else None


def _parse_claude_session(session_id: str, file_path: Path) -> SessionData:
    messages: list[Message] = []
    cwd = None
    branch = None
    started_at = None

    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            row = _safe_json(line)
            if not row:
                continue

            rtype = row.get("type")
            if rtype not in ("user", "assistant"):
                continue

            msg = row.get("message") or {}
            role = msg.get("role") or rtype
            text = _extract_claude_text(msg)
            text = _normalize(text)
            if not text:
                continue

            if _is_noise(text):
                continue

            messages.append(Message(role=role, text=text, timestamp=row.get("timestamp")))

            if not cwd and isinstance(row.get("cwd"), str):
                cwd = row["cwd"]
            if not branch and isinstance(row.get("gitBranch"), str):
                branch = row["gitBranch"]
            if not started_at and isinstance(row.get("timestamp"), str):
                started_at = row["timestamp"]

    return SessionData(
        provider="claude",
        session_id=session_id,
        source_file=file_path,
        cwd=cwd,
        branch=branch,
        started_at=started_at,
        messages=messages,
    )


def _find_codex_session_file(session_id: str) -> Optional[Path]:
    candidates: list[Path] = []
    for root in (CODEX_ROOT / "sessions", CODEX_ROOT / "archived_sessions"):
        if root.exists():
            candidates.extend(root.glob(f"**/*{session_id}*.jsonl"))

    for candidate in candidates:
        try:
            first_line = candidate.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            row = _safe_json(first_line)
            if row and row.get("type") == "session_meta":
                sid = ((row.get("payload") or {}).get("id"))
                if sid == session_id:
                    return candidate
        except Exception:
            continue

    for root in (CODEX_ROOT / "sessions", CODEX_ROOT / "archived_sessions"):
        if not root.exists():
            continue
        for candidate in root.glob("**/*.jsonl"):
            try:
                first_line = candidate.read_text(encoding="utf-8", errors="replace").splitlines()[0]
                row = _safe_json(first_line)
                if row and row.get("type") == "session_meta":
                    sid = ((row.get("payload") or {}).get("id"))
                    if sid == session_id:
                        return candidate
            except Exception:
                continue

    return None


def _extract_codex_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("text"), str):
            chunks.append(item["text"])
        elif isinstance(item.get("input_text"), str):
            chunks.append(item["input_text"])
    return "\n".join(chunks)


def _parse_codex_session(session_id: str, file_path: Path) -> SessionData:
    messages: list[Message] = []
    cwd = None
    branch = None
    started_at = None

    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            row = _safe_json(line)
            if not row:
                continue

            if row.get("type") == "session_meta":
                payload = row.get("payload") or {}
                if not cwd:
                    cwd = payload.get("cwd")
                if not started_at:
                    started_at = payload.get("timestamp")
                git = payload.get("git") or {}
                if not branch:
                    branch = git.get("branch")
                continue

            if row.get("type") == "response_item":
                payload = row.get("payload") or {}
                if payload.get("type") == "message" and payload.get("role") in ("user", "assistant"):
                    text = _normalize(_extract_codex_text(payload.get("content")))
                    if text and not _is_noise(text):
                        messages.append(
                            Message(
                                role=payload["role"],
                                text=text,
                                timestamp=row.get("timestamp"),
                            )
                        )

    return SessionData(
        provider="codex",
        session_id=session_id,
        source_file=file_path,
        cwd=cwd,
        branch=branch,
        started_at=started_at,
        messages=messages,
    )


def _find_kimi_session_file(session_id: str) -> Optional[Path]:
    """Kimi sessions: ~/.kimi/sessions/<workspace_hash>/<session_id>/context.jsonl"""
    sessions_root = KIMI_ROOT / "sessions"
    if not sessions_root.exists():
        return None
    # session_id is the UUID directory name
    matches = list(sessions_root.glob(f"*/{session_id}/context.jsonl"))
    return matches[0] if matches else None


def _extract_kimi_text(content: Any) -> str:
    """Extract visible text from kimi content (string or list of blocks).
    Kimi assistant content is a list of blocks with type: 'think' | 'text'.
    We skip 'think' blocks (internal reasoning) and extract 'text' blocks only.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            chunks.append(block["text"])
    return "\n".join(chunks)


def _parse_kimi_session(session_id: str, file_path: Path) -> SessionData:
    messages: list[Message] = []
    # Kimi doesn't embed cwd/branch in context.jsonl — infer from path
    cwd = str(file_path.parent.parent.parent.parent)  # best-effort
    started_at = None

    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            row = _safe_json(line)
            if not row:
                continue

            role = row.get("role")
            if role in ("_checkpoint",):
                # Extract timestamp from checkpoint if present
                if not started_at and isinstance(row.get("timestamp"), str):
                    started_at = row["timestamp"]
                continue

            if role not in ("user", "assistant"):
                continue

            text = _normalize(_extract_kimi_text(row.get("content", "")))
            if not text or _is_noise(text):
                continue

            ts = row.get("timestamp")
            messages.append(Message(role=role, text=text, timestamp=ts))
            if not started_at and ts:
                started_at = ts

    # Use file mtime as fallback for started_at
    if not started_at:
        import datetime as dt
        mtime = file_path.stat().st_mtime
        started_at = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).isoformat()

    return SessionData(
        provider="kimi",
        session_id=session_id,
        source_file=file_path,
        cwd=cwd,
        branch=None,
        started_at=started_at,
        messages=messages,
    )


def _format_ts(ts: Optional[str]) -> str:
    if not ts:
        return "unknown"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except Exception:
        return ts


def _last_user_intent(messages: Iterable[Message]) -> str:
    for msg in reversed(list(messages)):
        if msg.role == "user" and msg.text:
            return msg.text
    return "(No explicit user message found)"


def build_packet(data: SessionData, max_messages: int, full: bool) -> str:
    selected = data.messages if full else (data.messages[-max_messages:] if data.messages else [])
    last_intent = _normalize(_last_user_intent(selected), max_len=900)

    lines: list[str] = []
    lines.append("# Session Resume Packet")
    lines.append("")
    lines.append(f"- Provider: {data.provider}")
    lines.append(f"- Session ID: {data.session_id}")
    lines.append(f"- Source file: {data.source_file}")
    lines.append(f"- Started at: {_format_ts(data.started_at)}")
    lines.append(f"- Working directory: {data.cwd or 'unknown'}")
    lines.append(f"- Git branch: {data.branch or 'unknown'}")
    lines.append("")
    lines.append("## Last User Intent")
    lines.append("")
    lines.append(last_intent)
    lines.append("")
    lines.append("## Recent Conversation")
    lines.append("")
    if full:
        lines.append("_Mode: full transcript capture_")
        lines.append("")
    else:
        lines.append(f"_Mode: last {max_messages} messages_")
        lines.append("")

    if not selected:
        lines.append("_No user/assistant messages captured for this session._")
    else:
        for msg in selected:
            lines.append(f"### {msg.role.upper()} @ {_format_ts(msg.timestamp)}")
            lines.append(msg.text)
            lines.append("")

    lines.append("## Resume Prompt")
    lines.append("")
    lines.append("Use the packet above as authoritative context.")
    lines.append("Continue from the last user intent immediately.")
    lines.append("Do not ask to restate prior context unless a critical detail is missing.")
    lines.append("")

    return "\n".join(lines)


def resolve_session(session_id: str, provider: str) -> SessionData:
    claude_file = _find_claude_session_file(session_id)
    codex_file = _find_codex_session_file(session_id)
    kimi_file = _find_kimi_session_file(session_id)

    if provider == "claude":
        if not claude_file:
            raise FileNotFoundError(f"Claude session not found: {session_id}")
        return _parse_claude_session(session_id, claude_file)

    if provider == "codex":
        if not codex_file:
            raise FileNotFoundError(f"Codex session not found: {session_id}")
        return _parse_codex_session(session_id, codex_file)

    if provider == "kimi":
        if not kimi_file:
            raise FileNotFoundError(f"Kimi session not found: {session_id}")
        return _parse_kimi_session(session_id, kimi_file)

    # auto: pick the most recently modified match across all providers
    candidates: list[tuple[float, str, Path]] = []
    if claude_file:
        candidates.append((claude_file.stat().st_mtime, "claude", claude_file))
    if codex_file:
        candidates.append((codex_file.stat().st_mtime, "codex", codex_file))
    if kimi_file:
        candidates.append((kimi_file.stat().st_mtime, "kimi", kimi_file))

    if not candidates:
        raise FileNotFoundError(f"Session not found in Claude, Codex, or Kimi logs: {session_id}")

    _, best_provider, best_file = max(candidates, key=lambda t: t[0])
    if best_provider == "claude":
        return _parse_claude_session(session_id, best_file)
    if best_provider == "codex":
        return _parse_codex_session(session_id, best_file)
    return _parse_kimi_session(session_id, best_file)


def main() -> int:
    args = parse_args()
    data = resolve_session(args.session_id, args.provider)
    packet = build_packet(data, max_messages=max(4, args.max_messages), full=bool(args.full))

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.write_text(packet + "\n", encoding="utf-8")
        print(out_path)
    else:
        print(packet)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
