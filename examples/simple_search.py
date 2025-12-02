"""
Simple Search Example
=====================

This example demonstrates basic web search functionality using the
browser automation framework.

Usage:
    python examples/simple_search.py
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from softlight_automation_framework import Agent, BrowserSession
from softlight_automation_framework.llm import OpenAIClient


async def simple_search():
    """
    Perform a simple Google search and get the first result.
    """
    # Initialize the LLM client
    llm = OpenAIClient(model="gpt-4o")
    
    # Define the task
    task = "Search Google for 'Python programming tutorials' and tell me the title of the first result"
    
    print(f"🎯 Task: {task}\n")
    
    # Create browser session and run agent
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=10,  # Limit steps for a simple task
        )
        
        # Run the agent
        result = await agent.run()
        
        # Display results
        print("\n" + "=" * 50)
        print("📋 RESULTS")
        print("=" * 50)
        
        print(f"\n✅ Completed: {result.is_done()}")
        print(f"🎉 Success: {result.is_successful()}")
        print(f"📊 Steps taken: {result.number_of_steps()}")
        print(f"⏱️  Duration: {result.total_duration_seconds():.1f}s")
        
        if result.final_result():
            print(f"\n📝 Final Result:\n{result.final_result()}")
        
        # Show visited URLs
        urls = [u for u in result.urls() if u]
        if urls:
            print("\n🔗 Visited URLs:")
            for url in set(urls):
                print(f"   • {url[:70]}...")


if __name__ == "__main__":
    asyncio.run(simple_search())

