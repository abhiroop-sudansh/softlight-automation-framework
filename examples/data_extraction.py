"""
Data Extraction Example
=======================

This example demonstrates extracting structured data from web pages.

Usage:
    python examples/data_extraction.py
"""

import asyncio
import json
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

from softlight_automation_framework import Agent, BrowserSession
from softlight_automation_framework.llm import OpenAIClient


# Define structured output model
class NewsArticle(BaseModel):
    """A news article extracted from HackerNews."""
    title: str = Field(description="Article title")
    url: str = Field(description="Article URL")
    points: int = Field(description="Number of points/upvotes")
    

class HackerNewsTop(BaseModel):
    """Top stories from HackerNews."""
    articles: List[NewsArticle] = Field(description="List of top articles")


async def extract_hackernews():
    """
    Extract top stories from Hacker News.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    task = """
    1. Navigate to https://news.ycombinator.com/
    2. Extract the titles, URLs, and point counts of the top 5 stories
    3. Return the information in a structured format
    """
    
    print(f"🎯 Task: Extract HackerNews Top Stories\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=10,
        )
        
        result = await agent.run()
        
        print("\n📋 EXTRACTED DATA")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")


async def extract_weather():
    """
    Extract weather information for a city.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    city = input("Enter city name (default: New York): ").strip() or "New York"
    
    task = f"""
    1. Search Google for "weather in {city}"
    2. Extract the current weather information including:
       - Temperature
       - Weather condition (sunny, cloudy, etc.)
       - Humidity
       - Wind speed
    3. Return a summary of the current weather
    """
    
    print(f"\n🎯 Task: Get Weather for {city}\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=10,
        )
        
        result = await agent.run()
        
        print("\n🌤️  WEATHER INFORMATION")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")


async def extract_product_info():
    """
    Extract product information from a search.
    """
    llm = OpenAIClient(model="gpt-4o")
    
    product = input("Enter product to search (default: iPhone 15): ").strip() or "iPhone 15"
    
    task = f"""
    1. Search Google for "{product} price"
    2. Look for pricing information from multiple sources
    3. Extract and summarize:
       - Product name
       - Price range found
       - Where to buy
    4. Provide a summary of the pricing information found
    """
    
    print(f"\n🎯 Task: Find Prices for {product}\n")
    
    async with BrowserSession(headless=False) as browser:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_steps=15,
        )
        
        result = await agent.run()
        
        print("\n💰 PRODUCT INFORMATION")
        print("=" * 50)
        
        if result.final_result():
            print(f"\n{result.final_result()}")


if __name__ == "__main__":
    print("Data Extraction Examples")
    print("=" * 30)
    print("1. Extract HackerNews top stories")
    print("2. Get weather information")
    print("3. Search for product prices")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        asyncio.run(extract_hackernews())
    elif choice == "2":
        asyncio.run(extract_weather())
    elif choice == "3":
        asyncio.run(extract_product_info())
    else:
        print("Running default example (HackerNews)...")
        asyncio.run(extract_hackernews())

