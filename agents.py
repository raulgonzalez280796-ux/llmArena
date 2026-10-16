"""AutoGen adapter. Each instance owns its history and its tool list."""

import os
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient

from config import AgentConfig, SYSTEM_PROMPT
from logger import EventLogger
from tools import build_tools


def create_model_client(config: AgentConfig) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=config.model,
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
        include_name_in_message=False,
        parallel_tool_calls=False,
        max_retries=2,
        timeout=45.0,
        max_tokens=1024,
    )


def create_agent(
    config: AgentConfig,
    client: ChatCompletionClient,
    workspace: Path,
    log: EventLogger,
) -> AssistantAgent:
    return AssistantAgent(
        name=f"agent_{config.agent_id.lower()}",
        model_client=client,
        system_message=SYSTEM_PROMPT,
        tools=build_tools(config.agent_id, config.tool_names, workspace, log),
        max_tool_iterations=2,
        reflect_on_tool_use=False,
    )
