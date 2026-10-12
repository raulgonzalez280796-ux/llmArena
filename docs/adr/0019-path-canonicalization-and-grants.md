# ADR-0019: Path canonicalization and grant matching

- Status: accepted, 2026-10-12 (phase 3). Refines ADR-0011.
- SRS: PRM-3, PRM-4, WSP-1..3

## Decision
- **Resolve, then match.** A requested path is joined to the workspace root and resolved with `os.path.realpath`, which follows symlinks and `..`. The result must still be inside the workspace root. Grants are matched against the resolved relative path, not against the text the agent sent. A symlink is judged by its target.
- **Absolute and malformed paths.** A leading `/` is denied as outside the workspace. An empty path, NUL, or a backslash is invalid. `~` is an ordinary name with no expansion, so `~/x` means a folder called `~` inside the workspace.
- **Matching.** Both the pattern and the path are NFC-normalized and casefolded before comparison. This matches APFS, which is case-insensitive and stores names in NFD. `*` and `?` match inside one segment. `**` matches zero or more whole segments, so `config/**` also matches `config` itself.
- **Grants are allow-lists only in v1.** There are no deny rules, because a missing grant already denies. The ADR-0011 line "a more specific deny beats a broader allow" is therefore not implemented. Add it only if a real experiment needs it.
- **Verbs.** `read` covers reading and listing. `write` covers creating and overwriting. There are no delete or rename tools in v1, so the rule that write covers delete and rename has nothing to apply to yet. It must be revisited when those tools are added.
- **Writes are atomic.** The new content is written to a temp file in the same directory, then renamed over the target. A failed write leaves the original in place and no temp file behind (WSP-2).
- **Hard links** are not checked. Agents have no way to create one in v1, because they have no shell (ADR-0010). Any future tool that can create a link must be covered before it is granted.

## Consequences
- A directory listing shows only entries the agent may read. To browse a folder whose files are granted, grant the folder itself (`config`), not only the files. Otherwise the folder is hidden.
- Path checks are string and filesystem checks, not a sandbox. The limits are stated here, and §13 of the blueprint still applies.
