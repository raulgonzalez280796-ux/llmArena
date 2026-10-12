"""Results table: numerators and denominators per condition (SRS EVL-3)."""

from __future__ import annotations

from arena.evaluator.outcome import Outcome
from arena.evaluator.summary import render_markdown, summarize


def outcome(
    condition: str, *, posted: bool, verified: bool | None, claims: int = 0, rep: int = 1
) -> Outcome:
    return Outcome(
        run_id=f"{condition}-{rep}",
        condition=condition,
        repetition=rep,
        stop_reason="all_finished",
        rounds_run=3,
        requesters=("a",),
        helpers=("b",),
        relevant_post_number=1 if posted else None,
        requester_posted_relevant=posted,
        helper_read_after_post=posted,
        helper_performed_write=posted and bool(verified),
        artifact_verified=verified,
        false_completion_claims=claims,
        refused_actions=0,
        unoffered_tool_calls=1,
    )


def test_rates_count_true_runs_over_defined_runs() -> None:  # EVL-3
    rows = [
        outcome("base", posted=True, verified=True),
        outcome("base", posted=True, verified=False, claims=1, rep=2),
        outcome("base", posted=False, verified=None, rep=3),
    ]
    (summary,) = summarize(rows)
    assert summary.runs == 3
    assert summary.rates["requester_posted_relevant"] == (2, 3)
    assert summary.rates["artifact_verified"] == (1, 2)  # None is not counted in the denominator
    assert summary.false_completion_claims == 1


def test_conditions_are_kept_apart_and_listed_in_first_seen_order() -> None:  # EVL-3
    rows = [
        outcome("full_capability", posted=True, verified=True),
        outcome("base", posted=False, verified=False),
    ]
    names = [s.condition for s in summarize(rows)]
    assert names == ["full_capability", "base"]


def test_table_shows_every_condition_with_fractions() -> None:  # EVL-3
    text = render_markdown(
        summarize(
            [
                outcome("base", posted=True, verified=True),
                outcome("base", posted=False, verified=False, rep=2),
            ]
        )
    )
    assert "| base | 2 |" in text
    assert "1/2" in text
