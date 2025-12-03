#!/usr/bin/env python3
"""
SOFTLIGHT AUTOMATION AGENT
=================================

A simple command-line interface where you (Agent A) give commands 
and the system (Agent B) performs them while capturing screenshots.

Usage:
    python run_agent.py

Example session:
    Agent A command: Create a new project named softlight AI in my linear.
    Agent B: Working on task...
    Agent B: Task completed and screenshots saved to datasets/create_a_new_project_named_softlight_ai_in_my_linear/

    Agent A command: Turn on toggle "Start week on Monday" in Notion.
    Agent B: Working on task...
    Agent B: Task completed and screenshots saved to datasets/turn_on_toggle_start_week_on_monday_in_notion/
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("softlight_automation_framework").setLevel(logging.WARNING)

# Default session file location
SESSION_FILE = Path(__file__).parent / "browser_session.json"


def print_banner():
    """Print welcome banner."""
    print()
    print("=" * 60)
    print("🤖 SOFTLIGHT AUTOMATION AGENT")
    print("=" * 60)
    print()
    print("Give commands and Agent B will perform them in the browser,")
    print("capturing screenshots at each step.")
    print()
    print("Examples:")
    print('  • How do I Create a new project named ‘Softlight AI Automation’ with summary ’New Era in AI’ in Linear?')
    print('  • How can I Create a new issue titled Fix login bug with priority High in Linear?')
    
    
    # Check for saved session
    if SESSION_FILE.exists():
        print("✅ Saved login session found - will use your logged-in accounts")
    else:
        print(" Run 'python save_session.py' to save your login sessions")
    print()
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)
    print()


async def run_task(command: str, headless: bool = False, keep_open: bool = False) -> None:
    """Run a single task and capture the workflow."""
    from softlight_automation_framework.tutorial.agent import TutorialAgent
    from softlight_automation_framework.llm.openai_client import OpenAIClient
    from softlight_automation_framework.browser.session import BrowserSession
    
    print(f"\nAgent B: Working on task...")
    
    # Check for saved session
    session_file = str(SESSION_FILE) if SESSION_FILE.exists() else None
    if session_file:
        print(f"Agent B: Loading saved login session...")
    
    print(f"Agent B: Opening browser and navigating...")
    
    browser = None
    try:
        llm = OpenAIClient(model="gpt-4o")
        
        # Create browser session that we control
        browser = BrowserSession(
            headless=headless,
            session_file=session_file,
        )
        await browser.start()
        
        agent = TutorialAgent(
            query=command,
            llm=llm,
            browser=browser,
            max_steps=20,
            headless=headless,
            datasets_dir="./datasets",
            session_file=session_file,
        )
        
        workflow = await agent.run()
        
        if workflow.success:
            print(f"\nAgent B: ✅ Task completed and screenshots saved.")
            print(f"Agent B: 📁 Output: {workflow.output_dir}/")
            print(f"Agent B: 📸 {len(workflow.steps)} screenshots captured")
        else:
            print(f"\nAgent B: ⚠️ Task partially completed.")
            print(f"Agent B: 📁 Output: {workflow.output_dir}/")
            print(f"Agent B: 📸 {len(workflow.steps)} screenshots captured")
        
        # Show steps summary
        if workflow.steps:
            print(f"\nAgent B: Steps performed:")
            for step in workflow.steps[:5]:
                print(f"         {step.step_number}. {step.instruction}")
            if len(workflow.steps) > 5:
                print(f"         ... and {len(workflow.steps) - 5} more steps")
        
        # Keep browser open until user decides to close
        if keep_open and browser.is_active:
            print(f"\nAgent B: 🌐 Browser is open. Enjoy!")
            print(f"Agent B: Type 'close' or press Enter to close the browser...")
            while True:
                try:
                    user_input = input().strip().lower()
                    if user_input in ["", "close", "exit", "quit", "q"]:
                        break
                except (KeyboardInterrupt, EOFError):
                    break
        
        # Close browser
        if browser.is_active:
            print(f"Agent B: Closing browser...")
            await browser.stop()
        
    except Exception as e:
        print(f"\nAgent B: ❌ Error: {e}")
        try:
            if browser and browser.is_active:
                await browser.stop()
        except:
            pass


async def interactive_mode(headless: bool = False, keep_open: bool = False):
    """Run the interactive Agent A ↔ Agent B session with persistent browser."""
    from softlight_automation_framework.tutorial.agent import TutorialAgent
    from softlight_automation_framework.llm.openai_client import OpenAIClient
    from softlight_automation_framework.browser.session import BrowserSession
    
    print_banner()
    print("🔄 Persistent session mode: Browser stays open between commands!")
    print("   Type 'quit' to exit and close browser.\n")
    
    # Check for saved session
    session_file = str(SESSION_FILE) if SESSION_FILE.exists() else None
    if session_file:
        print("✅ Loaded saved login session\n")
    
    # Create ONE persistent browser session
    browser = BrowserSession(
        headless=headless,
        session_file=session_file,
    )
    await browser.start()
    print("Agent B: 🌐 Browser opened and ready!\n")
    
    llm = OpenAIClient(model="gpt-4o")
    command_count = 0
    
    try:
        while True:
            try:
                # Get command from Agent A (user)
                command = input("Agent A: ").strip()
                
                # Check for exit
                if command.lower() in ["quit", "exit", "q"]:
                    print("\nAgent B: Closing browser and exiting... Goodbye! 👋")
                    break
                
                if command == "":
                    continue
                
                command_count += 1
                print(f"\nAgent B: Working on it...")
                
                # Run task on the SAME browser session
                await run_task_on_browser(
                    command=command,
                    browser=browser,
                    llm=llm,
                    command_count=command_count,
                )
                
                print()  # Add spacing
                
            except KeyboardInterrupt:
                print("\n\nAgent B: Interrupted. Type 'quit' to exit or continue with another command.")
                continue
            except EOFError:
                break
    finally:
        # Close browser when done
        if browser.is_active:
            await browser.stop()
            print("Agent B: Browser closed.")


async def run_task_on_browser(
    command: str,
    browser,
    llm,
    command_count: int,
) -> None:
    """Run a task on an existing browser session."""
    from softlight_automation_framework.tutorial.agent import TutorialAgent
    from softlight_automation_framework.tutorial.capture import WorkflowCapture
    from softlight_automation_framework.tutorial.views import TaskRequest
    import re
    
    # Create task request
    task_name = re.sub(r'[^a-z0-9]+', '_', command[:50].lower()).strip('_')
    task_name = f"{command_count:02d}_{task_name}"
    
    task_request = TaskRequest(query=command, max_steps=20)
    
    # Create capture for this command
    capture = WorkflowCapture(
        base_dir="./datasets",
        task_request=TaskRequest(query=command),
    )
    # Override task name to include command number
    capture.task_name = task_name
    capture.output_dir = capture.base_dir / task_name
    capture.screenshots_dir = capture.output_dir / "screenshots"
    capture.output_dir.mkdir(parents=True, exist_ok=True)
    capture.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Infer app from command
        app_name = "Browser"
        app_url = browser.current_url if browser.current_url else "about:blank"
        
        # Check for app mentions in command
        command_lower = command.lower()
        app_mappings = {
            "linear": ("Linear", "https://linear.app"),
            "notion": ("Notion", "https://notion.so"),
            "github": ("GitHub", "https://github.com"),
            "youtube": ("YouTube", "https://youtube.com"),
            "google": ("Google", "https://google.com"),
        }
        
        for key, (name, url) in app_mappings.items():
            if key in command_lower:
                app_name = name
                # Only set URL if we need to navigate (mentions "open" or "go to")
                if any(word in command_lower for word in ["open", "go to", "navigate", "visit"]):
                    app_url = url
                break
        
        # Start workflow capture (ensure app_url is never None)
        capture.start_workflow(
            app_name=app_name,
            app_url=app_url if app_url else "about:blank",
        )
        
        # Capture initial state
        state = await browser.get_state(force_refresh=True)
        capture.capture_state(
            url=state.url,
            title=state.title,
            screenshot_b64=state.screenshot_b64 or "",
            action_taken=f"Starting from current page",
            action_type="initial",
            annotation=f"Current state before command",
        )
        
        # Create agent with existing browser
        agent = TutorialAgent(
            query=command,
            llm=llm,
            browser=browser,
            max_steps=15,
            datasets_dir="./datasets",
        )
        
        # Override to not navigate if already on the right app
        current_url = browser.current_url or ""
        if app_name != "Browser" and app_name.lower() in current_url.lower():
            agent._app_url = None  # Don't navigate, already there
        elif "open" in command_lower or "go to" in command_lower:
            agent._app_url = app_url
        else:
            agent._app_url = None  # Continue from current page
        
        # Override capture
        agent.capture = capture
        agent._owns_browser = False  # Don't let agent close the browser
        
        # Run the agent
        workflow = await agent.run()
        
        if workflow.success:
            print(f"Agent B: ✅ Done! Screenshots saved to datasets/{task_name}/")
        else:
            print(f"Agent B: ⚠️ Partially done. Screenshots saved to datasets/{task_name}/")
            
    except Exception as e:
        print(f"Agent B: ❌ Error: {e}")


async def single_command_mode(command: str, headless: bool = False, keep_open: bool = False):
    """Run a single command and exit."""
    print(f"\nAgent A command: {command}")
    
    # Auto-detect if task needs browser to stay open
    needs_open = keep_open or any(word in command.lower() for word in [
        "play", "watch", "video", "youtube", "music", "spotify", "listen"
    ])
    
    await run_task(command, headless=headless, keep_open=needs_open)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Agent A ↔ Agent B Tutorial System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agent.py
  python run_agent.py --headless
  python run_agent.py -c "Search for Python on GitHub"
  python run_agent.py -c "Play a song on YouTube" --keep-open
        """
    )
    parser.add_argument(
        "-c", "--command",
        type=str,
        default=None,
        help="Run a single command and exit"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)"
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Keep browser open after task completion (auto-enabled for video/music)"
    )
    
    args = parser.parse_args()
    
    if args.command:
        asyncio.run(single_command_mode(args.command, headless=args.headless, keep_open=args.keep_open))
    else:
        asyncio.run(interactive_mode(headless=args.headless, keep_open=args.keep_open))


if __name__ == "__main__":
    main()

