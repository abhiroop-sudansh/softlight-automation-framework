"""
Form Automation Example
=======================

This example demonstrates automated form filling and submission.

Usage:
    python examples/form_automation.py
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from softlight_automation_framework import Agent, BrowserSession
from softlight_automation_framework.llm import OpenAIClient


async def fill_contact_form():
    """
    Navigate to a demo form and fill it out.
    
    Uses httpbin.org as a safe test endpoint.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    # Task with specific instructions
    task = """
    1. Navigate to https://httpbin.org/forms/post
    2. Fill out the form with the following information:
       - Customer name: John Doe
       - Telephone: 555-1234
       - E-mail: john.doe@example.com
       - Size: Large
       - Check "Bacon" topping
       - Leave a comment: "This is an automated test"
    3. Submit the form
    4. Tell me what response you received after submission
    """
    
    print(f"🎯 Task: Form Automation Demo\n")
    print(task)
    print("\n" + "=" * 50)
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=15,
            extend_system_message="Be careful to fill each form field correctly before submitting.",
        )
        
        result = await agent.run()
        
        print("\n📋 RESULTS")
        print("=" * 50)
        print(f"\n✅ Completed: {result.is_done()}")
        print(f"🎉 Success: {result.is_successful()}")
        
        if result.final_result():
            print(f"\n📝 Response:\n{result.final_result()}")


async def search_and_fill():
    """
    More complex example: search for a form and fill it.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    task = """
    1. Go to Google and search for "HTML form test page"
    2. Click on one of the results that has a simple test form
    3. If you find a form, fill in any text fields with test data
    4. Report what form you found and what fields it had
    """
    
    print(f"🎯 Task: Search and Fill Form\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=20,
        )
        
        result = await agent.run()
        
        print("\n📋 RESULTS")
        print("=" * 50)
        print(f"\n✅ Completed: {result.is_done()}")
        
        if result.final_result():
            print(f"\n📝 Report:\n{result.final_result()}")


if __name__ == "__main__":
    print("Choose an example:")
    print("1. Fill a demo contact form")
    print("2. Search and fill a form")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(fill_contact_form())
    elif choice == "2":
        asyncio.run(search_and_fill())
    else:
        print("Running default example...")
        asyncio.run(fill_contact_form())

