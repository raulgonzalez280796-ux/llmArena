"""Fixed A/B scheduling. No board watcher, automatic routing, or shared chat."""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from config import CONTINUE_PROMPT
from logger import EventLogger


async def run_experiment(
    agents: dict[str, AssistantAgent],
    initial_prompts: dict[str, str],
    log: EventLogger,
    max_rounds: int,
    verbose: bool = True,
) -> None:
    for round_number in range(1, max_rounds + 1):
        for agent_id in ("A", "B"):
            prompt = (
                initial_prompts[agent_id]
                if round_number == 1 else CONTINUE_PROMPT
            )
            log.emit(
                "turn_started", agent_id=agent_id,
                round=round_number, prompt=prompt,
            )
            if verbose:
                print(f"Round {round_number}/{max_rounds}: agent {agent_id}")
            async for event in agents[agent_id].run_stream(task=prompt):
                if isinstance(event, TaskResult):
                    # These messages were already emitted by run_stream.
                    log.emit(
                        "turn_finished", agent_id=agent_id,
                        round=round_number, stop_reason=event.stop_reason,
                    )
                else:
                    log.emit(
                        "agent_event", agent_id=agent_id,
                        round=round_number, event=event.model_dump(mode="json"),
                    )

    # Completion of A's task is evaluated by the caller after this loop.
    # It does not cause a special wake-up or an early change of schedule.
