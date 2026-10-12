# ADR-0021: The shared board

- Status: accepted, 2026-10-12 (phase 4)
- SRS: BRD-1..6
- Blueprint: §11 (message envelope), §12 (visibility), §20 (metrics)

## Decision
- **One board per trial.** It is a service object, not a file. Agents reach it only through `read_board` and `post_to_board`, and only if their grant includes `board: true` (ADR-0004).
- **Append-only.** Posts are numbered from 1 with no gaps. There is no method to edit, delete or clear a post (BRD-2).
- **Sender from the gateway.** The gateway passes its own agent id to the board. The post tool takes only `text`, so a model that adds `sender` gets a rejected call (BRD-3). Nothing in the model's output can name another author.
- **Pull only.** A post reaches an agent's context only when that agent calls `read_board`. Nothing is pushed into a prompt (BRD-4, ADR-0006). The framework test `test_peer_does_not_see_a_post_until_it_reads_the_board` checks this with two agents.
- **Reads return everything.** `read_board` returns all posts so far, as `#n [author] text`. The board is small, at most 20 posts per agent. What an agent saw is logged in full (LOG-2).
- **Limits (defaults the user approved):**
  - 20 posts per agent per trial;
  - 2,000 characters per post, counted as Python characters;
  - an empty or whitespace-only post is rejected.
  A refused post is not recorded, and the refusal is logged with a reason (`post_limit`, `post_too_long`, `post_empty`).
- **Neutral descriptions.** The tool descriptions say what the tool does and nothing else. They never suggest asking others. Tests check this (`tests/agents/test_prompts.py`).

## Consequences
- The limits are constants in `arena/board/service.py`. They are part of the condition fingerprint (ADR-0022). If an experiment needs different limits, they move into the experiment schema and the fingerprint changes with them.
- Board use is observable as events (`tool_call` with `read_board` or `post_to_board`), so the outcome measures in blueprint §20 can be counted from the log.
- Direct messages, discovery and notifications are absent by design (ADR-0005, ADR-0006).
