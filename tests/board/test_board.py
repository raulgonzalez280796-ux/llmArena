"""The shared board: append-only, numbered, sender-stamped, limited (SRS BRD-1..3, BRD-5)."""

from __future__ import annotations

import pytest

from arena.board.service import (
    MAX_POST_CHARS,
    MAX_POSTS_PER_AGENT,
    Board,
    BoardLimitReached,
    EmptyPost,
    PostTooLong,
)


def test_posts_are_numbered_from_one_with_the_sender_recorded() -> None:  # BRD-2, BRD-3
    board = Board()
    first = board.post("a", "first note")
    second = board.post("b", "second note")
    assert (first.number, first.sender, first.text) == (1, "a", "first note")
    assert (second.number, second.sender) == (2, "b")
    assert [p.number for p in board.posts()] == [1, 2]


def test_board_offers_no_way_to_edit_or_remove_a_post() -> None:  # BRD-2
    board = Board()
    board.post("a", "kept")
    for name in ("edit", "update", "delete", "remove", "clear", "replace"):
        assert not hasattr(board, name), name


def test_posts_are_returned_in_order_and_are_immutable() -> None:  # BRD-2
    board = Board()
    board.post("a", "one")
    board.post("b", "two")
    snapshot = board.posts()
    board.post("a", "three")
    assert [p.text for p in snapshot] == ["one", "two"]
    with pytest.raises(AttributeError):
        snapshot[0].text = "changed"  # type: ignore[misc]


def test_each_agent_has_its_own_post_limit() -> None:  # BRD-5
    board = Board(max_posts_per_agent=2)
    board.post("a", "1")
    board.post("a", "2")
    with pytest.raises(BoardLimitReached):
        board.post("a", "3")
    assert board.post("b", "still allowed").number == 3


def test_default_post_limit_is_twenty_per_agent() -> None:  # BRD-5
    board = Board()
    for i in range(MAX_POSTS_PER_AGENT):
        board.post("a", f"post {i}")
    with pytest.raises(BoardLimitReached):
        board.post("a", "one too many")


def test_post_length_limit_is_enforced_in_characters() -> None:  # BRD-5
    board = Board()
    board.post("a", "x" * MAX_POST_CHARS)
    with pytest.raises(PostTooLong):
        board.post("a", "x" * (MAX_POST_CHARS + 1))


def test_empty_post_is_rejected() -> None:
    with pytest.raises(EmptyPost):
        Board().post("a", "   ")


def test_refused_post_is_not_recorded() -> None:  # BRD-2
    board = Board(max_posts_per_agent=1)
    board.post("a", "ok")
    with pytest.raises(BoardLimitReached):
        board.post("a", "refused")
    assert [p.text for p in board.posts()] == ["ok"]
