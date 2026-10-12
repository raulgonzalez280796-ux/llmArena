# ADR-0027: Tool picker in the UI and separate board read and post grants

- Status: accepted, 2026-10-12 (approved by the researcher)
- Amends: ADR-0004 (board access is one grant), SRS BRD-6
- SRS: PRM-1, BRD-6, UI-2

## Decision
- **Board grant split.** `board: true` is replaced by `board_read` (offers `read_board`) and `board_post` (offers `post_to_board`). Reading and posting can now be given separately, so a post-only or read-only agent is a valid condition.
- **One rule for offered tools.** `offered_tools(grants)` in `arena/tools/gateway.py` is the only place that maps grants to tools. The gateway uses it, and the UI asks the server for it through `POST /api/tools`. The preview therefore cannot disagree with the runtime.
- **Picker in the UI.** Each agent card has one checkbox per tool group:
  - read files (`list_files`, `read_file`), with path globs;
  - write files (`write_file`), with path globs;
  - read the board (`read_board`);
  - post to the board (`post_to_board`).

  A path field is enabled only when its checkbox is ticked. The page refuses to save a ticked file tool that has no path, because that would offer a tool with nothing it may touch. `finish` is shown as always offered.
- **Live preview.** The card shows the tools the server reports for the current choices, and it updates on every change.

## Consequences
- `list_files` and `read_file` are one checkbox, because listing follows reading (ADR-0019). Separating them would need a schema change, so it is not done.
- The example experiment now uses `board_read` and `board_post`. Its `board_off` condition turns off both.
- The UI can save an agent that has no tools at all. The preview then shows that it can only finish, so the researcher sees it before the run.
