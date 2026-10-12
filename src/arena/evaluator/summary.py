"""Results per condition with numerators and denominators (SRS EVL-3; ADR-0013)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from arena.evaluator.outcome import Outcome

RATE_METRICS = (
    "requester_posted_relevant",
    "helper_read_after_post",
    "helper_performed_write",
    "artifact_verified",
)


@dataclass(frozen=True)
class ConditionSummary:
    condition: str
    runs: int
    rates: dict[str, tuple[int, int]]  # metric -> (true count, runs where it is defined)
    false_completion_claims: int
    refused_actions: int
    unoffered_tool_calls: int
    stop_reasons: dict[str, int]


def summarize(outcomes: Iterable[Outcome]) -> list[ConditionSummary]:
    grouped: dict[str, list[Outcome]] = {}
    for outcome in outcomes:
        grouped.setdefault(outcome.condition, []).append(outcome)

    summaries: list[ConditionSummary] = []
    for condition, rows in grouped.items():
        rates: dict[str, tuple[int, int]] = {}
        for metric in RATE_METRICS:
            values = [getattr(r, metric) for r in rows]
            defined = [v for v in values if v is not None]
            rates[metric] = (sum(1 for v in defined if v), len(defined))
        summaries.append(
            ConditionSummary(
                condition=condition,
                runs=len(rows),
                rates=rates,
                false_completion_claims=sum(r.false_completion_claims for r in rows),
                refused_actions=sum(r.refused_actions for r in rows),
                unoffered_tool_calls=sum(r.unoffered_tool_calls for r in rows),
                stop_reasons=dict(Counter(r.stop_reason for r in rows)),
            )
        )
    return summaries


def render_markdown(summaries: list[ConditionSummary]) -> str:
    header = (
        "| condition | runs | "
        + " | ".join(RATE_METRICS)
        + " | false completions | refused | unoffered calls |"
    )
    rule = "|" + "---|" * (len(RATE_METRICS) + 6)
    lines = [header, rule]
    for s in summaries:
        cells = [f"{s.rates[m][0]}/{s.rates[m][1]}" for m in RATE_METRICS]
        lines.append(
            f"| {s.condition} | {s.runs} | "
            + " | ".join(cells)
            + f" | {s.false_completion_claims} | {s.refused_actions} | {s.unoffered_tool_calls} |"
        )
    return "\n".join(lines) + "\n"
