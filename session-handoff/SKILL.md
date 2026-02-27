---
name: session-handoff
description: Generate a reusable context handoff from a Claude or Codex session ID so another agent can resume work without losing context. Use this skill when the user asks to continue/switch sessions, recover context from session logs, or resume from a specific session ID.
---

# Session Handoff

Use this skill to resume work from a previous Claude/Codex session by session ID.

## Workflow

1. Get the session ID from the user.
2. Run the handoff script:
```bash
python3 ~/.agents/skills/session-handoff/scripts/session_handoff.py <SESSION_ID> --provider auto -o /tmp/session-handoff.md
```
3. Read the generated packet and continue from `Last User Intent` + `Recent Conversation`.
4. If the user asks to paste/share the packet, return `/tmp/session-handoff.md` content.

## Provider selection

- Default: `--provider auto` (tries Claude and Codex, picks the match).
- Force Claude: `--provider claude`
- Force Codex: `--provider codex`

## Useful options

- `--max-messages 24` to include more history.
- `--full` to export the full captured session conversation.
- No `-o` to print directly in terminal.

## Expected output

The script generates a `Session Resume Packet` with:

- provider/source file metadata
- last explicit user intent
- recent user/assistant conversation
- a ready-to-use resume prompt
