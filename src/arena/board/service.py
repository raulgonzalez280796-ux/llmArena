"""The shared board: one append-only list of numbered posts per trial (SRS BRD-1..3, BRD-5).

The board has no edit or delete. The sender is supplied by the caller, and the Tool Gateway
always passes the identity it was built with, so a model cannot name another sender.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Final

MAX_POSTS_PER_AGENT: Final = 20
MAX_POST_CHARS: Final = 2000


class BoardLimitReached(Exception):
    """The agent has used its post allowance for this trial."""


class PostTooLong(ValueError):
    """The post exceeds the character limit."""


class EmptyPost(ValueError):
    """The post has no text after trimming whitespace."""


@dataclass(frozen=True)
class Post:
    number: int
    sender: str
    text: str


class Board:
    def __init__(
        self,
        *,
        max_posts_per_agent: int = MAX_POSTS_PER_AGENT,
        max_post_chars: int = MAX_POST_CHARS,
    ) -> None:
        self._posts: list[Post] = []
        self._counts: Counter[str] = Counter()
        self._max_posts_per_agent = max_posts_per_agent
        self._max_post_chars = max_post_chars

    def post(self, sender: str, text: str) -> Post:
        if not text.strip():
            raise EmptyPost
        if len(text) > self._max_post_chars:
            raise PostTooLong
        if self._counts[sender] >= self._max_posts_per_agent:
            raise BoardLimitReached
        record = Post(number=len(self._posts) + 1, sender=sender, text=text)
        self._posts.append(record)
        self._counts[sender] += 1
        return record

    def posts(self) -> tuple[Post, ...]:
        return tuple(self._posts)

    @property
    def max_posts_per_agent(self) -> int:
        return self._max_posts_per_agent

    @property
    def max_post_chars(self) -> int:
        return self._max_post_chars
