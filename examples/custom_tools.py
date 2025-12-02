"""
Custom Tools Example
====================

This example demonstrates how to extend the framework with custom actions/tools.

Usage:
    python examples/custom_tools.py
"""

import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from softlight_automation_framework import Agent, BrowserSession
from softlight_automation_framework.llm import OpenAIClient
from softlight_automation_framework.tools import ToolRegistry, ActionResult
from softlight_automation_framework.tools.actions import register_default_actions


# Custom action parameter models
class CalculatorParams(BaseModel):
    """Parameters for calculator action."""
    expression: str = Field(description="Mathematical expression to evaluate")


class TimestampParams(BaseModel):
    """Parameters for timestamp action."""
    format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Datetime format string"
    )


class StoreDataParams(BaseModel):
    """Parameters for data storage action."""
    key: str = Field(description="Key to store data under")
    value: str = Field(description="Value to store")


def create_custom_registry() -> ToolRegistry:
    """
    Create a registry with custom actions alongside default ones.
    """
    registry = ToolRegistry()
    
    # Register all default browser actions
    register_default_actions(registry)
    
    # In-memory data store for the session
    data_store = {}
    
    # Custom action: Calculator
    @registry.action(
        description="Evaluate a mathematical expression",
        param_model=CalculatorParams,
        requires_browser=False,  # This action doesn't need the browser
    )
    async def calculate(params: CalculatorParams) -> ActionResult:
        """Safely evaluate mathematical expressions."""
        try:
            # Safe evaluation (only math operations)
            allowed_names = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'pow': pow,
            }
            result = eval(params.expression, {"__builtins__": {}}, allowed_names)
            return ActionResult(
                extracted_content=f"Result: {params.expression} = {result}",
                long_term_memory=f"Calculated: {params.expression} = {result}",
            )
        except Exception as e:
            return ActionResult(error=f"Calculation failed: {e}")
    
    # Custom action: Get timestamp
    @registry.action(
        description="Get the current date and time",
        param_model=TimestampParams,
        requires_browser=False,
    )
    async def get_timestamp(params: TimestampParams) -> ActionResult:
        """Get current timestamp."""
        now = datetime.now()
        formatted = now.strftime(params.format)
        return ActionResult(
            extracted_content=f"Current time: {formatted}",
        )
    
    # Custom action: Store data
    @registry.action(
        description="Store data for later retrieval during this session",
        param_model=StoreDataParams,
        requires_browser=False,
    )
    async def store_data(params: StoreDataParams) -> ActionResult:
        """Store a key-value pair."""
        data_store[params.key] = params.value
        return ActionResult(
            extracted_content=f"Stored '{params.key}' = '{params.value}'",
            long_term_memory=f"Data stored: {params.key}",
        )
    
    # Custom action: Retrieve data
    @registry.action(
        description="Retrieve previously stored data",
        requires_browser=False,
    )
    async def retrieve_data(key: str) -> ActionResult:
        """Retrieve a stored value."""
        if key in data_store:
            value = data_store[key]
            return ActionResult(
                extracted_content=f"Retrieved '{key}' = '{value}'",
            )
        return ActionResult(
            error=f"Key '{key}' not found in data store",
        )
    
    # Custom action: List stored keys
    @registry.action(
        description="List all keys in the data store",
        requires_browser=False,
    )
    async def list_stored_keys() -> ActionResult:
        """List all stored keys."""
        if data_store:
            keys = list(data_store.keys())
            return ActionResult(
                extracted_content=f"Stored keys: {', '.join(keys)}",
            )
        return ActionResult(
            extracted_content="Data store is empty",
        )
    
    # Custom action with browser: Highlight elements
    @registry.action(
        description="Highlight all interactive elements on the page",
    )
    async def highlight_all_elements(browser_session) -> ActionResult:
        """Highlight interactive elements for debugging."""
        script = """
            document.querySelectorAll('a, button, input, select, textarea, [onclick], [tabindex]')
                .forEach((el, i) => {
                    el.style.outline = '2px solid red';
                    el.style.outlineOffset = '2px';
                });
            return document.querySelectorAll('a, button, input, select, textarea, [onclick], [tabindex]').length;
        """
        try:
            count = await browser_session.execute_script(script)
            return ActionResult(
                extracted_content=f"Highlighted {count} interactive elements",
            )
        except Exception as e:
            return ActionResult(error=f"Failed to highlight: {e}")
    
    print(f"✅ Registered {len(registry)} actions (including custom ones)")
    return registry


async def demo_custom_tools():
    """
    Demonstrate using custom tools in a task.
    """
    llm = OpenAIClient(model="gpt-4o")
    registry = create_custom_registry()
    
    task = """
    Perform the following tasks:
    
    1. First, get the current timestamp and store it with key "start_time"
    2. Calculate the result of: (25 * 4) + (100 / 5)
    3. Go to https://news.ycombinator.com/
    4. Use highlight_all_elements to see interactive elements
    5. Store the number of stories visible as "story_count"
    6. Get the timestamp again and calculate how many seconds passed
    7. Report all stored data and the time elapsed
    """
    
    print("🎯 Task: Custom Tools Demo\n")
    print(task)
    print("\n" + "=" * 50)
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            tools=registry,
            max_steps=15,
        )
        
        result = await agent.run()
        
        print("\n📋 RESULTS")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")
        
        # Show actions used
        print("\n🔧 Actions Used:")
        for action in result.action_names():
            print(f"   • {action}")


async def demo_calculator_only():
    """
    Simple demo using just the calculator action.
    """
    llm = OpenAIClient(model="gpt-4o")
    registry = create_custom_registry()
    
    expression = input("Enter math expression (default: 123 * 456 + 789): ").strip()
    expression = expression or "123 * 456 + 789"
    
    task = f"""
    Calculate the result of: {expression}
    
    Then explain what the calculation represents.
    """
    
    print(f"\n🎯 Task: Calculate {expression}\n")
    
    async with BrowserSession(headless=True) as browser:  # Headless since we don't need browser
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            tools=registry,
            max_steps=5,
        )
        
        result = await agent.run()
        
        print("\n📋 RESULT")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")


if __name__ == "__main__":
    print("Custom Tools Examples")
    print("=" * 30)
    print("1. Full custom tools demo")
    print("2. Calculator only demo")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(demo_custom_tools())
    elif choice == "2":
        asyncio.run(demo_calculator_only())
    else:
        print("Running full demo...")
        asyncio.run(demo_custom_tools())

