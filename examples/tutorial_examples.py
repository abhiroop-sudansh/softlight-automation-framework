#!/usr/bin/env python3
"""
Example tasks demonstrating the Tutorial Generator's generalizability.

This script shows how the system can handle various types of requests
across different web applications - without any hardcoded knowledge
of these specific tasks.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from softlight_automation_framework.tutorial.agent import TutorialAgent, run_tutorial
from softlight_automation_framework.llm.openai_client import OpenAIClient


# Example tasks demonstrating generalizability
# These are NOT hardcoded into the system - they're just examples
# The system should handle ANY similar request

EXAMPLE_TASKS = [
    # Navigation & Discovery Tasks
    {
        "query": "How do I find trending repositories on GitHub?",
        "start_url": "https://github.com",
        "category": "Navigation",
    },
    {
        "query": "How do I browse the front page of Hacker News?",
        "start_url": "https://news.ycombinator.com",
        "category": "Navigation",
    },
    
    # Search Tasks
    {
        "query": "How do I search for Python projects on GitHub?",
        "start_url": "https://github.com",
        "category": "Search",
    },
    {
        "query": "How do I search for images of cats on DuckDuckGo?",
        "start_url": "https://duckduckgo.com",
        "category": "Search",
    },
    
    # Information Extraction Tasks
    {
        "query": "How do I find the weather forecast on weather.gov?",
        "start_url": "https://weather.gov",
        "category": "Information",
    },
    {
        "query": "How do I look up a Wikipedia article about machine learning?",
        "start_url": "https://wikipedia.org",
        "category": "Information",
    },
    
    # E-commerce Tasks (browsing only - no purchases)
    {
        "query": "How do I browse product categories on Amazon?",
        "start_url": "https://amazon.com",
        "category": "E-commerce",
    },
    
    # Documentation Tasks
    {
        "query": "How do I find the documentation for Python requests library?",
        "start_url": "https://docs.python-requests.org",
        "category": "Documentation",
    },
]


async def run_single_example(
    task: dict,
    llm: OpenAIClient,
    datasets_dir: str = "./datasets",
    headless: bool = False,
) -> dict:
    """Run a single example task and return results."""
    print(f"\n{'='*60}")
    print(f"Category: {task['category']}")
    print(f"Query: {task['query']}")
    print(f"URL: {task['start_url']}")
    print(f"{'='*60}")
    
    try:
        agent = TutorialAgent(
            query=task["query"],
            llm=llm,
            start_url=task["start_url"],
            max_steps=15,
            headless=headless,
            datasets_dir=datasets_dir,
        )
        
        workflow = await agent.run()
        
        result = {
            "task": task["query"],
            "category": task["category"],
            "success": workflow.success,
            "steps": len(workflow.steps),
            "output_dir": workflow.output_dir,
            "duration": workflow.total_duration_seconds,
        }
        
        print(f"\n✅ Completed: {len(workflow.steps)} steps captured")
        print(f"   Output: {workflow.output_dir}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {
            "task": task["query"],
            "category": task["category"],
            "success": False,
            "error": str(e),
        }


async def run_all_examples(
    headless: bool = False,
    datasets_dir: str = "./datasets",
    max_examples: int = None,
):
    """Run all example tasks."""
    print("🎬 Tutorial Generator - Example Tasks")
    print("="*60)
    print("This demonstrates how the system handles various tasks")
    print("across different web applications WITHOUT hardcoded logic.")
    print("="*60)
    
    llm = OpenAIClient(model="gpt-4o")
    tasks = EXAMPLE_TASKS[:max_examples] if max_examples else EXAMPLE_TASKS
    
    results = []
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Running: {task['query'][:50]}...")
        result = await run_single_example(
            task=task,
            llm=llm,
            datasets_dir=datasets_dir,
            headless=headless,
        )
        results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r.get("success"))
    print(f"Total Tasks: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    
    print("\nResults by Category:")
    categories = set(r["category"] for r in results)
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        cat_success = sum(1 for r in cat_results if r.get("success"))
        print(f"  {cat}: {cat_success}/{len(cat_results)}")
    
    print(f"\nAll workflows saved to: {datasets_dir}")
    
    return results


async def run_quick_demo():
    """Run a quick demo with just 2 tasks."""
    print("🚀 Quick Demo - Running 2 example tasks")
    
    demo_tasks = [
        {
            "query": "Show me the top stories on Hacker News",
            "start_url": "https://news.ycombinator.com",
            "category": "Navigation",
        },
        {
            "query": "Search for 'hello world' on DuckDuckGo",
            "start_url": "https://duckduckgo.com",
            "category": "Search",
        },
    ]
    
    llm = OpenAIClient(model="gpt-4o")
    
    for task in demo_tasks:
        await run_single_example(
            task=task,
            llm=llm,
            datasets_dir="./datasets",
            headless=False,
        )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tutorial Generator Examples")
    parser.add_argument("--quick", action="store_true", help="Run quick demo (2 tasks)")
    parser.add_argument("--all", action="store_true", help="Run all examples")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--max", type=int, default=None, help="Max examples to run")
    parser.add_argument("--output", default="./datasets", help="Output directory")
    
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(run_quick_demo())
    elif args.all:
        asyncio.run(run_all_examples(
            headless=args.headless,
            datasets_dir=args.output,
            max_examples=args.max,
        ))
    else:
        # Default: run quick demo
        print("Usage:")
        print("  python tutorial_examples.py --quick    # Quick 2-task demo")
        print("  python tutorial_examples.py --all      # Run all examples")
        print("  python tutorial_examples.py --all --headless  # Headless mode")
        print()
        asyncio.run(run_quick_demo())

