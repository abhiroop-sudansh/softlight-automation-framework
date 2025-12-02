"""Agent module - core agent implementation and execution loop."""

from softlight_automation_framework.agent.executor import Agent
from softlight_automation_framework.agent.prompts import SystemPrompt, build_user_message
from softlight_automation_framework.agent.message_manager import MessageManager
from softlight_automation_framework.agent.views import (
    AgentState,
    AgentHistory,
    AgentHistoryList,
    AgentStepInfo,
)

__all__ = [
    "Agent",
    "SystemPrompt",
    "build_user_message",
    "MessageManager",
    "AgentState",
    "AgentHistory",
    "AgentHistoryList",
    "AgentStepInfo",
]

