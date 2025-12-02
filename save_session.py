#!/usr/bin/env python3
"""
Session Manager - Save your login sessions for the Agent
=========================================================

This script opens a browser where you can manually log in to your accounts
(Linear, Notion, GitHub, etc.). When you're done, the session is saved
so Agent B can use your logged-in state.

Usage:
    python save_session.py

Then:
    1. Log in to Linear, Notion, or any other service
    2. Press Enter in the terminal when done
    3. Your session is saved!
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Session storage location
SESSION_FILE = Path(__file__).parent / "browser_session.json"


async def save_session():
    """Open browser for manual login and save session."""
    from playwright.async_api import async_playwright
    
    print()
    print("=" * 60)
    print("🔐 Session Manager - Log in to your accounts")
    print("=" * 60)
    print()
    print("A browser window will open. Please:")
    print()
    print("  1. Navigate to the sites you want to use:")
    print("     • https://linear.app")
    print("     • https://notion.so")
    print("     • https://github.com")
    print("     • Any other sites...")
    print()
    print("  2. Log in to each account")
    print()
    print("  3. Come back here and press ENTER to save your session")
    print()
    print("=" * 60)
    print()
    
    input("Press ENTER to open the browser...")
    
    async with async_playwright() as p:
        # Launch browser with persistent context
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        
        # Open initial pages for common services
        page = await context.new_page()
        await page.goto("https://linear.app")
        
        print()
        print("🌐 Browser opened!")
        print()
        print("Log in to your accounts, then come back here.")
        print()
        
        input("Press ENTER when you're done logging in...")
        
        # Save storage state (cookies, localStorage, etc.)
        await context.storage_state(path=str(SESSION_FILE))
        
        await browser.close()
    
    print()
    print("=" * 60)
    print(f"✅ Session saved to: {SESSION_FILE}")
    print("=" * 60)
    print()
    print("Your login sessions are now saved!")
    print("Run 'python run_agent.py' and your sessions will be loaded.")
    print()


async def clear_session():
    """Clear saved session."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("✅ Session cleared!")
    else:
        print("No saved session found.")


async def test_session():
    """Test if saved session works."""
    if not SESSION_FILE.exists():
        print("❌ No saved session found. Run 'python save_session.py' first.")
        return
    
    from playwright.async_api import async_playwright
    
    print("Testing saved session...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=str(SESSION_FILE),
            viewport={"width": 1280, "height": 720},
        )
        
        page = await context.new_page()
        await page.goto("https://linear.app")
        
        print()
        print("🌐 Browser opened with saved session!")
        print("Check if you're logged in to Linear.")
        print()
        
        input("Press ENTER to close...")
        
        await browser.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Session Manager")
    parser.add_argument("--clear", action="store_true", help="Clear saved session")
    parser.add_argument("--test", action="store_true", help="Test saved session")
    
    args = parser.parse_args()
    
    if args.clear:
        asyncio.run(clear_session())
    elif args.test:
        asyncio.run(test_session())
    else:
        asyncio.run(save_session())


if __name__ == "__main__":
    main()

