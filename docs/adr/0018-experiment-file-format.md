# ADR-0018: Experiment file format and validation

- Status: accepted, 2026-10-12 (phase 3)
- Blueprint: §7 (schema sketch), SRS EXP-1..5, AGT-1

## Context
§7 of the blueprint sketches an agent configuration in YAML. The file must be easy to read, reject typos, and never hold a secret.

## Decision
- An experiment is one YAML file, parsed with pydantic models. Every model is strict: an unknown field is an error, and so is a duplicate mapping key (PyYAML would otherwise keep the last one silently).
- The schema holds agents (`model`, `task`, `grants`), `fixture`, `limits`, `repetitions`, and named `conditions`. `limits` and `repetitions` have no defaults, so each experiment states them.
- A task is written inline in the YAML, not in a separate prompt file. The condition fingerprint (ADR-0012) hashes the resolved file, so the prompt is covered either way.
- A condition is a set of overrides keyed by dotted path, such as `agents.a.grants.write`. An override may only change a field that already exists. A typo or an unknown agent is an error, and every override is validated when the experiment loads.
- Canonical form: `dump_experiment` is the only text form. Files in `experiments/` must equal the dump of their own parse (EXP-2). The UI (phase 7) will save through the same function.
- API keys are referenced only by variable name (`api_key_env`), and the name must look like an environment variable, so a key pasted into the field fails validation. A real provider needs a key variable. The `scripted` provider takes none, and exists only for dry runs and tests. Real model names are chosen with the user in phase 8.

## Consequences
- Adding a new experiment field means changing the schema, the canonical dump and every example file together. That is intended.
- The `scripted` provider can be written into a real-looking experiment. The runner (phase 5) must refuse to run a batch unless the user explicitly allows scripted agents.
