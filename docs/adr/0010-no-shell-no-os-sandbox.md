# ADR-0010: No shell or code execution in v1

- Status: accepted, 2026-10-12
- Deciders: user (blueprint §6, §13)

## Decision
No agent gets a shell, code execution or network tool in v1. Every action goes through our trusted Tool Gateway. No OS sandbox (Docker, srt) is installed.

## Consequences
"No grant means no access" holds at the API level, and reports must say so. Observing technical bypasses needs a later phase with OS-level isolation, and that phase needs the user's approval for the install.
