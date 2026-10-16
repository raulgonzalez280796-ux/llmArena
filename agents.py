"""AutoGen adapter. Each instance owns its history and its tool list."""

import os
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.anthropic import AnthropicChatCompletionClient

from config import AgentConfig, SYSTEM_PROMPT
from logger import EventLogger
from tools import build_tools


def create_model_client(config: AgentConfig) -> AnthropicChatCompletionClient:
    return AnthropicChatCompletionClient(
        model=config.model,
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "claude-opus",
            "structured_output": False,
            "multiple_system_messages": False,
        },
        timeout=45.0,
        max_retries=2,
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
        max_tool_iterations=1,
        reflect_on_tool_use=False,
    )
