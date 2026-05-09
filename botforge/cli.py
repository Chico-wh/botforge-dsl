"""
BotForge CLI

Entry point for the `botforge` command.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .analyzer import analyze_file
from .exceptions import BotForgeError
from .generator import generate
from .parser import parse_file

app = typer.Typer(
    name="botforge",
    help="BotForge — Compile Python robot DSL to C++ for Arduino and beyond.",
    add_completion=False,
)
console = Console()


@app.command()
def build(
    source: Path = typer.Argument(..., help="Path to the .py DSL file"),
    target: str = typer.Option("arduino", "--target", "-t", help="Compilation target (arduino)"),
    output: Path = typer.Option(Path("output"), "--output", "-o", help="Base output directory"),
) -> None:
    """Compile a BotForge DSL file into C++ source code."""

    if not source.exists():
        console.print(f"[red]Error:[/red] File not found: {source}")
        raise typer.Exit(code=1)

    if not source.suffix == ".py":
        console.print(f"[red]Error:[/red] Expected a .py file, got: {source}")
        raise typer.Exit(code=1)

    console.print(Panel(f"[bold cyan]BotForge[/bold cyan] — building [yellow]{source}[/yellow]"))

    try:
        console.print("  [dim]→ Analyzing DSL...[/dim]")
        analyze_file(source)

        console.print("  [dim]→ Parsing AST...[/dim]")
        program = parse_file(source, target=target)

        out_dir = output / program.name
        console.print(f"  [dim]→ Generating C++ for target [bold]{target}[/bold]...[/dim]")
        generate(program, out_dir)

        console.print(f"\n[green]✓ Done![/green] Output written to: [bold]{out_dir}/[/bold]")
        console.print(f"  • {out_dir}/main.cpp")
        console.print(f"  • {out_dir}/README_GENERATED.md")

    except BotForgeError as exc:
        console.print(f"\n[red]✗ {exc}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"\n[red]✗ Unexpected error: {exc}[/red]")
        raise typer.Exit(code=1)


@app.command()
def targets() -> None:
    """List all supported compilation targets."""
    console.print("[bold]Supported targets:[/bold]")
    console.print("  • [cyan]arduino[/cyan]  — Arduino Uno / Mega / Nano (V0.1)")
    console.print("  • [dim]esp32[/dim]    — ESP32 (planned V0.3)")
    console.print("  • [dim]ros2[/dim]     — ROS 2 node (planned V0.5)")


if __name__ == "__main__":
    app()
