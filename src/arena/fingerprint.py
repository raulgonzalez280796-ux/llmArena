"""Condition fingerprint: a hash of everything an agent reads in one condition (SRS LOG-5).

A run record stores this hash, so two runs with the same fingerprint saw the same instructions,
tool descriptions, board limits, refusal wording and task text.
"""

from __future__ import annotations

import hashlib
import json

from arena.agents.prompts import NEUTRAL_INSTRUCTIONS, ROUND_MESSAGE
from arena.board.service import MAX_POST_CHARS, MAX_POSTS_PER_AGENT
from arena.config.schema import Experiment
from arena.tools import board_tools, files, finish
from arena.tools.gateway import REFUSAL


def condition_fingerprint(experiment: Experiment) -> str:
    payload = {
        "experiment": experiment.model_dump(mode="json", exclude_none=True, exclude={"conditions"}),
        "instructions": NEUTRAL_INSTRUCTIONS,
        "tool_descriptions": {
            "list_files": files.LIST_DESCRIPTION,
            "read_file": files.READ_DESCRIPTION,
            "write_file": files.WRITE_DESCRIPTION,
            "read_board": board_tools.READ_BOARD_DESCRIPTION,
            "post_to_board": board_tools.POST_TO_BOARD_DESCRIPTION,
            "finish": finish.FINISH_DESCRIPTION,
        },
        "round_message": ROUND_MESSAGE,
        "board_limits": {
            "max_posts_per_agent": MAX_POSTS_PER_AGENT,
            "max_post_chars": MAX_POST_CHARS,
        },
        "refusal": REFUSAL,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
