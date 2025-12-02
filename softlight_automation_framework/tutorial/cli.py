"""CLI for Tutorial Generation System - Agent A interface."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """🎬 Tutorial Generator - Capture UI workflows automatically."""
    setup_logging(verbose)


@cli.command()
@click.argument("query")
@click.option("--url", "-u", default=None, help="Starting URL (optional)")
@click.option("--app", "-a", default=None, help="App name hint (e.g., 'linear', 'notion')")
@click.option("--max-steps", "-s", default=20, help="Maximum steps to attempt")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
@click.option("--output", "-o", default="./datasets", help="Output directory for captured workflows")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
def capture(
    query: str,
    url: Optional[str],
    app: Optional[str],
    max_steps: int,
    headless: bool,
    output: str,
    model: str,
):
    """
    Capture a UI workflow for a given task.
    
    Examples:
    
        tutorial capture "How do I create a project in Linear?"
        
        tutorial capture "Filter issues by status" --app linear
        
        tutorial capture "Create a new database" --url https://notion.so
    """
    console.print(Panel(
        f"[bold cyan]🎬 Tutorial Capture[/bold cyan]\n\n"
        f"[yellow]Query:[/yellow] {query}\n"
        f"[yellow]App:[/yellow] {app or 'Auto-detect'}\n"
        f"[yellow]URL:[/yellow] {url or 'Auto-detect'}\n"
        f"[yellow]Max Steps:[/yellow] {max_steps}\n"
        f"[yellow]Output:[/yellow] {output}",
        title="Starting Capture",
        border_style="cyan"
    ))
    
    async def run():
        from softlight_automation_framework.tutorial.agent import run_tutorial
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Capturing workflow...", total=None)
            
            try:
                workflow = await run_tutorial(
                    query=query,
                    start_url=url,
                    app_hint=app,
                    model=model,
                    headless=headless,
                    max_steps=max_steps,
                    datasets_dir=output,
                )
                
                progress.remove_task(task)
                
                # Display results
                _display_workflow_results(workflow)
                
            except Exception as e:
                progress.remove_task(task)
                console.print(f"\n[red]Error:[/red] {e}")
                raise click.ClickException(str(e))
    
    asyncio.run(run())


@cli.command()
@click.option("--output", "-o", default="./datasets", help="Output directory")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--headless", is_flag=True, help="Run in headless mode")
def interactive(output: str, model: str, headless: bool):
    """
    Interactive mode - Agent A gives commands, Agent B captures tutorials.
    
    Type your task requests and the system will capture the workflow.
    """
    console.print(Panel(
        "[bold cyan]🤖 Agent A Interface[/bold cyan]\n\n"
        "Enter task requests and Agent B will demonstrate how to perform them.\n"
        "Screenshots will be saved to the datasets folder.\n\n"
        "[dim]Type 'quit' or 'exit' to stop.[/dim]",
        title="Interactive Tutorial Mode",
        border_style="cyan"
    ))
    
    async def run_interactive():
        from softlight_automation_framework.tutorial.agent import TutorialAgent
        from softlight_automation_framework.llm.openai_client import OpenAIClient
        
        llm = OpenAIClient(model=model)
        
        while True:
            console.print()
            query = Prompt.ask("[bold green]Agent A[/bold green]")
            
            if query.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if not query.strip():
                continue
            
            console.print(f"\n[cyan]Agent B:[/cyan] Starting to capture workflow for: [italic]{query}[/italic]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Capturing workflow...", total=None)
                
                try:
                    agent = TutorialAgent(
                        query=query,
                        llm=llm,
                        max_steps=20,
                        headless=headless,
                        datasets_dir=output,
                    )
                    
                    workflow = await agent.run()
                    
                    progress.remove_task(task)
                    _display_workflow_results(workflow)
                    
                except Exception as e:
                    progress.remove_task(task)
                    console.print(f"[red]Error:[/red] {e}")
    
    asyncio.run(run_interactive())


@cli.command()
@click.option("--output", "-o", default="./datasets", help="Output directory")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--headless", is_flag=True, help="Run in headless mode")
def examples(output: str, model: str, headless: bool):
    """
    Run example tasks to demonstrate the system.
    
    Captures workflows for several pre-defined example tasks.
    """
    example_tasks = [
        {
            "query": "How do I search for repositories on GitHub?",
            "url": "https://github.com",
            "description": "GitHub repository search",
        },
        {
            "query": "How do I find the top stories on Hacker News?",
            "url": "https://news.ycombinator.com",
            "description": "Hacker News exploration",
        },
        {
            "query": "How do I search for images on DuckDuckGo?",
            "url": "https://duckduckgo.com",
            "description": "DuckDuckGo image search",
        },
        {
            "query": "How do I find articles on Wikipedia?",
            "url": "https://wikipedia.org",
            "description": "Wikipedia article search",
        },
    ]
    
    console.print(Panel(
        "[bold cyan]📚 Example Tasks[/bold cyan]\n\n"
        "Running example tasks to demonstrate the tutorial capture system.\n"
        "Each task will open a browser and capture the workflow.",
        title="Example Demonstrations",
        border_style="cyan"
    ))
    
    # Display tasks
    table = Table(title="Tasks to Capture")
    table.add_column("#", style="dim")
    table.add_column("Description", style="cyan")
    table.add_column("Query", style="white")
    
    for i, task in enumerate(example_tasks, 1):
        table.add_row(str(i), task["description"], task["query"][:50] + "...")
    
    console.print(table)
    console.print()
    
    if not click.confirm("Run these example tasks?"):
        return
    
    async def run_examples():
        from softlight_automation_framework.tutorial.agent import run_tutorial
        
        for i, task in enumerate(example_tasks, 1):
            console.print(f"\n[bold]Task {i}/{len(example_tasks)}:[/bold] {task['description']}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                prog_task = progress.add_task(f"Capturing: {task['query'][:40]}...", total=None)
                
                try:
                    workflow = await run_tutorial(
                        query=task["query"],
                        start_url=task["url"],
                        model=model,
                        headless=headless,
                        max_steps=15,
                        datasets_dir=output,
                    )
                    
                    progress.remove_task(prog_task)
                    
                    status = "[green]✓ Success[/green]" if workflow.success else "[yellow]⚠ Partial[/yellow]"
                    console.print(f"  {status} - {len(workflow.steps)} steps captured")
                    console.print(f"  [dim]Saved to: {workflow.output_dir}[/dim]")
                    
                except Exception as e:
                    progress.remove_task(prog_task)
                    console.print(f"  [red]✗ Error:[/red] {e}")
        
        console.print("\n[bold green]All example tasks completed![/bold green]")
        console.print(f"[dim]Workflows saved to: {output}[/dim]")
    
    asyncio.run(run_examples())


@cli.command()
@click.argument("task_name")
@click.option("--datasets-dir", "-d", default="./datasets", help="Datasets directory")
def view(task_name: str, datasets_dir: str):
    """
    View a captured workflow.
    
    Shows the tutorial markdown and step information.
    """
    task_dir = Path(datasets_dir) / task_name
    
    if not task_dir.exists():
        # Try to find partial match
        datasets_path = Path(datasets_dir)
        if datasets_path.exists():
            matches = [d for d in datasets_path.iterdir() if d.is_dir() and task_name in d.name]
            if matches:
                task_dir = matches[0]
                console.print(f"[dim]Found: {task_dir.name}[/dim]")
    
    if not task_dir.exists():
        raise click.ClickException(f"Task not found: {task_name}")
    
    # Read and display tutorial
    tutorial_path = task_dir / "tutorial.md"
    if tutorial_path.exists():
        md_content = tutorial_path.read_text()
        console.print(Markdown(md_content))
    else:
        console.print(f"[yellow]No tutorial.md found in {task_dir}[/yellow]")
    
    # Show screenshots list
    screenshots_dir = task_dir / "screenshots"
    if screenshots_dir.exists():
        screenshots = sorted(screenshots_dir.glob("*.png"))
        if screenshots:
            console.print(f"\n[bold]Screenshots ({len(screenshots)}):[/bold]")
            for ss in screenshots:
                console.print(f"  • {ss.name}")


@cli.command()
@click.option("--datasets-dir", "-d", default="./datasets", help="Datasets directory")
def list_tasks(datasets_dir: str):
    """List all captured workflows."""
    datasets_path = Path(datasets_dir)
    
    if not datasets_path.exists():
        console.print(f"[yellow]No datasets directory found at {datasets_dir}[/yellow]")
        return
    
    tasks = [d for d in datasets_path.iterdir() if d.is_dir()]
    
    if not tasks:
        console.print("[yellow]No captured workflows found.[/yellow]")
        return
    
    table = Table(title="Captured Workflows")
    table.add_column("Task Name", style="cyan")
    table.add_column("Steps", style="green")
    table.add_column("Status", style="yellow")
    
    for task_dir in sorted(tasks):
        # Count screenshots
        screenshots_dir = task_dir / "screenshots"
        num_screenshots = len(list(screenshots_dir.glob("*.png"))) if screenshots_dir.exists() else 0
        
        # Check for workflow.json
        workflow_json = task_dir / "workflow.json"
        if workflow_json.exists():
            import json
            data = json.loads(workflow_json.read_text())
            status = "✓ Complete" if data.get("success") else "⚠ Incomplete"
        else:
            status = "? Unknown"
        
        table.add_row(task_dir.name, str(num_screenshots), status)
    
    console.print(table)


def _display_workflow_results(workflow) -> None:
    """Display workflow capture results."""
    console.print()
    
    # Summary table
    table = Table(title="Capture Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Task", workflow.original_query[:60] + "..." if len(workflow.original_query) > 60 else workflow.original_query)
    table.add_row("Application", workflow.app_name)
    table.add_row("Steps Captured", str(len(workflow.steps)))
    table.add_row("Duration", f"{workflow.total_duration_seconds:.1f}s" if workflow.total_duration_seconds else "N/A")
    table.add_row("Status", "[green]✓ Success[/green]" if workflow.success else "[red]✗ Failed[/red]")
    
    console.print(table)
    
    # Output location
    console.print(Panel(
        f"[bold]Output Directory:[/bold] {workflow.output_dir}\n\n"
        f"[dim]• tutorial.md - Markdown tutorial\n"
        f"• workflow.json - Workflow metadata\n"
        f"• screenshots/ - Step screenshots[/dim]",
        title="📁 Files Saved",
        border_style="green"
    ))
    
    # Steps preview
    if workflow.steps:
        console.print("\n[bold]Steps:[/bold]")
        for step in workflow.steps[:5]:  # Show first 5 steps
            console.print(f"  {step.step_number}. {step.instruction}")
        if len(workflow.steps) > 5:
            console.print(f"  [dim]... and {len(workflow.steps) - 5} more steps[/dim]")


def main():
    """Main entry point for tutorial CLI."""
    cli()


if __name__ == "__main__":
    main()

