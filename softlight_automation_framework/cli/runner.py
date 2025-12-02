"""CLI runner for browser automation tasks."""

import asyncio
import logging
import sys
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from softlight_automation_framework.core.config import Config
from softlight_automation_framework.core.logging import setup_logging
from softlight_automation_framework.browser.session import BrowserSession
from softlight_automation_framework.llm.openai_client import OpenAIClient
from softlight_automation_framework.agent.executor import Agent
from softlight_automation_framework.agent.views import AgentHistoryList

console = Console()


def setup_cli_logging(verbose: bool = False) -> None:
    """Set up logging for CLI."""
    level = "DEBUG" if verbose else "INFO"
    
    # Use rich handler for pretty output
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=False,
        )]
    )
    
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


async def run_task(
    task: str,
    model: str = "gpt-4o",
    headless: bool = False,
    max_steps: int = 20,
    use_vision: bool = True,
    save_history: Optional[str] = None,
    verbose: bool = False,
) -> AgentHistoryList:
    """
    Run a browser automation task.
    
    Args:
        task: Task description
        model: LLM model to use
        headless: Run browser headless
        max_steps: Maximum steps
        use_vision: Include screenshots
        save_history: Path to save history JSON
        verbose: Verbose output
        
    Returns:
        AgentHistoryList with results
    """
    console.print(Panel(
        f"[bold blue]Task:[/bold blue] {task}",
        title="🤖 Browser Automation Agent",
        border_style="blue"
    ))
    
    # Initialize LLM
    llm = OpenAIClient(model=model)
    console.print(f"[dim]Using model: {model}[/dim]")
    
    # Run with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Launching browser...", total=None)
        
        async with BrowserSession(headless=headless) as browser:
            progress.update(
                progress.task_ids[0],
                description="Running agent..."
            )
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_steps=max_steps,
                use_vision=use_vision,
            )
            
            history = await agent.run()
    
    # Display results
    display_results(history)
    
    # Save history if requested
    if save_history:
        history.save_to_file(save_history)
        console.print(f"\n[dim]History saved to: {save_history}[/dim]")
    
    return history


def display_results(history: AgentHistoryList) -> None:
    """Display agent results in a nice format."""
    console.print()
    
    # Summary table
    table = Table(title="Execution Summary", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Steps", str(history.number_of_steps()))
    table.add_row("Duration", f"{history.total_duration_seconds():.1f}s")
    table.add_row("Completed", "✅ Yes" if history.is_done() else "❌ No")
    table.add_row(
        "Success",
        "✅ Yes" if history.is_successful() else "❌ No" if history.is_successful() is False else "⏳ Unknown"
    )
    
    if history.has_errors():
        errors = [e for e in history.errors() if e]
        table.add_row("Errors", str(len(errors)))
    
    console.print(table)
    
    # Final result
    result = history.final_result()
    if result:
        console.print(Panel(
            result[:1000] + "..." if len(result) > 1000 else result,
            title="📋 Result",
            border_style="green" if history.is_successful() else "red"
        ))
    
    # Visited URLs
    urls = [u for u in history.urls() if u]
    if urls:
        unique_urls = list(dict.fromkeys(urls))[:5]  # Last 5 unique URLs
        console.print("\n[bold]Visited URLs:[/bold]")
        for url in unique_urls:
            console.print(f"  • {url[:80]}{'...' if len(url) > 80 else ''}")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🤖 Browser Automation Framework - AI-powered web automation"""
    pass


@cli.command()
@click.argument("task")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--headless", "-h", is_flag=True, help="Run browser in headless mode")
@click.option("--max-steps", "-s", default=20, help="Maximum steps")
@click.option("--no-vision", is_flag=True, help="Disable screenshots")
@click.option("--save", "-o", help="Save history to JSON file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(
    task: str,
    model: str,
    headless: bool,
    max_steps: int,
    no_vision: bool,
    save: Optional[str],
    verbose: bool,
):
    """Run a browser automation task.
    
    Examples:
    
        browser-agent run "Search Google for Python tutorials"
        
        browser-agent run "Get the weather in New York" --headless
        
        browser-agent run "Find the price of iPhone 15" -m gpt-4o-mini -s 10
    """
    setup_cli_logging(verbose)
    
    try:
        asyncio.run(run_task(
            task=task,
            model=model,
            headless=headless,
            max_steps=max_steps,
            use_vision=not no_vision,
            save_history=save,
            verbose=verbose,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option("--headless", "-h", is_flag=True, help="Run browser in headless mode")
def interactive(headless: bool):
    """Start an interactive browser session.
    
    Opens a browser and lets you enter tasks one at a time.
    """
    setup_cli_logging()
    
    console.print(Panel(
        "Enter tasks to execute. Type 'quit' to exit.",
        title="🤖 Interactive Mode",
        border_style="blue"
    ))
    
    async def interactive_loop():
        llm = OpenAIClient()
        
        async with BrowserSession(headless=headless) as browser:
            while True:
                try:
                    task = console.input("\n[bold blue]Task:[/bold blue] ")
                    
                    if task.lower() in ("quit", "exit", "q"):
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    
                    if not task.strip():
                        continue
                    
                    agent = Agent(
                        task=task,
                        llm=llm,
                        browser=browser,
                        max_steps=20,
                    )
                    
                    history = await agent.run()
                    display_results(history)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
    
    try:
        asyncio.run(interactive_loop())
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def info():
    """Show framework information and configuration."""
    config = Config.from_env()
    
    table = Table(title="Configuration", border_style="blue")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # LLM settings
    table.add_row("LLM Model", config.llm.model)
    table.add_row("API Key Set", "✅ Yes" if config.llm.api_key else "❌ No")
    
    # Browser settings
    table.add_row("Headless", "Yes" if config.browser.headless else "No")
    table.add_row("Viewport", f"{config.browser.viewport_width}x{config.browser.viewport_height}")
    table.add_row("Timeout", f"{config.browser.timeout}ms")
    
    # Agent settings
    table.add_row("Max Steps", str(config.agent.max_steps))
    table.add_row("Use Vision", "Yes" if config.agent.use_vision else "No")
    
    console.print(table)
    
    if not config.llm.api_key:
        console.print("\n[yellow]⚠️  OPENAI_API_KEY not set. Set it in your environment or .env file.[/yellow]")


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()

