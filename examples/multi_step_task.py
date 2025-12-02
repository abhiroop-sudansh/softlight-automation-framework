"""
Multi-Step Task Example
=======================

This example demonstrates complex multi-step browser automation tasks
that require planning and execution across multiple pages.

Usage:
    python examples/multi_step_task.py
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from softlight_automation_framework import Agent, BrowserSession
from softlight_automation_framework.llm import OpenAIClient
from softlight_automation_framework.tools import ToolRegistry, ActionResult
from softlight_automation_framework.tools.actions import register_default_actions


async def research_task():
    """
    Perform a research task that requires visiting multiple pages.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    task = """
    Research the following topic and compile a brief report:
    
    Topic: "Latest developments in AI agents for web automation"
    
    Steps:
    1. Search Google for recent news about AI web automation agents
    2. Visit at least 2 different relevant articles
    3. Extract key points from each article
    4. Compile a summary report with:
       - Main developments in the field
       - Key companies/projects mentioned
       - Potential future trends
    
    Provide a well-organized summary at the end.
    """
    
    print("🎯 Task: AI Web Automation Research\n")
    print(task)
    print("\n" + "=" * 50)
    
    async with BrowserSession(headless=False, save_screenshots=True) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=30,  # More steps for complex task
            extend_system_message="""
            For this research task:
            - Take notes as you browse
            - Visit multiple sources for comprehensive coverage
            - Synthesize information into a coherent summary
            """,
        )
        
        result = await agent.run()
        
        print("\n📋 RESEARCH REPORT")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")
        
        # Show action summary
        print("\n📊 Execution Summary:")
        print(f"   Steps: {result.number_of_steps()}")
        print(f"   Duration: {result.total_duration_seconds():.1f}s")
        print(f"   Actions: {', '.join(result.action_names()[:10])}...")


async def comparison_task():
    """
    Compare products/services across multiple websites.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    item = input("What would you like to compare? (default: laptop prices): ").strip()
    item = item or "laptop prices under $1000"
    
    task = f"""
    Compare {item} across different sources:
    
    1. Search for "{item}" on Google
    2. Visit at least 2-3 different websites with relevant information
    3. Extract pricing/feature information from each
    4. Create a comparison summary including:
       - Source/website name
       - Key findings from each
       - Recommendation based on findings
    
    Provide a clear comparison at the end.
    """
    
    print(f"🎯 Task: Compare {item}\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=25,
        )
        
        result = await agent.run()
        
        print("\n📋 COMPARISON RESULTS")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")


async def custom_workflow():
    """
    Demonstrate custom action with multi-step workflow.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    # Create registry with custom action
    registry = ToolRegistry()
    register_default_actions(registry)
    
    # Add a custom note-taking action
    @registry.action("Save a note to memory for the final report")
    async def save_note(note: str, category: str = "general") -> ActionResult:
        """Save a note during research."""
        memory = f"[{category.upper()}] {note}"
        return ActionResult(
            extracted_content=f"Saved note: {note}",
            long_term_memory=memory,
        )
    
    task = """
    Investigate what's trending on the tech news today:
    
    1. Go to https://news.ycombinator.com/
    2. Identify the top 3 trending topics
    3. For each topic, use save_note to record key information
    4. Visit one article for more details
    5. Compile all notes into a final tech news digest
    """
    
    print("🎯 Task: Tech News Digest with Custom Actions\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            tools=registry,
            max_steps=20,
        )
        
        result = await agent.run()
        
        print("\n📰 TECH NEWS DIGEST")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")
        
        # Show agent thoughts
        thoughts = result.model_thoughts()
        if thoughts:
            print("\n🧠 Agent's Thoughts During Execution:")
            for i, thought in enumerate(thoughts[-3:], 1):  # Last 3 thoughts
                print(f"\n   Step {i}:")
                if thought.memory:
                    print(f"   Memory: {thought.memory[:100]}...")


if __name__ == "__main__":
    print("Multi-Step Task Examples")
    print("=" * 30)
    print("1. Research AI web automation")
    print("2. Compare products across websites")
    print("3. Custom workflow with note-taking")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        asyncio.run(research_task())
    elif choice == "2":
        asyncio.run(comparison_task())
    elif choice == "3":
        asyncio.run(custom_workflow())
    else:
        print("Running default example (research)...")
        asyncio.run(research_task())

