"""CLI entry-point for LegacyShift.

Usage:
    legacy-shift migrate path/to/BankAccount.java
    legacy-shift migrate path/to/BankAccount.java --output-dir ./out --max-retries 5
    legacy-shift explain path/to/BankAccount.java
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from legacy_shift import __version__
from legacy_shift.config import get_settings
from legacy_shift.graph.workflow import build_graph
from legacy_shift.parser import get_parser
from legacy_shift.parser.ast_parser import ParsedCode
from legacy_shift.parser.cobol_parser import CobolParsedCode
from legacy_shift.tracing.observability import init_tracing


def _source_language_from_path(path: str) -> str:
    """Infer source language from file extension."""
    suf = Path(path).suffix.lower()
    if suf in (".cbl", ".cob"):
        return "cobol"
    return "java"

console = Console()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
        stream=sys.stderr,
    )


def _read_source(path: str) -> str:
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise SystemExit(1)
    return p.read_text(encoding="utf-8")


@click.group()
@click.version_option(__version__, prog_name="legacy-shift")
def main() -> None:
    """LegacyShift — AI-powered legacy code migration tool."""


@main.command()
@click.argument("source_file")
@click.option("--output-dir", "-o", default=".", help="Directory to write output files.")
@click.option("--max-retries", "-r", default=None, type=int, help="Max test-fix iterations.")
@click.option("--model", "-m", default=None, help="LLM model to use (LiteLLM format).")
@click.option("--log-level", default=None, help="Log level (DEBUG, INFO, WARNING, ERROR).")
def migrate(
    source_file: str,
    output_dir: str,
    max_retries: int | None,
    model: str | None,
    log_level: str | None,
) -> None:
    """Run the full migration pipeline: explain → test → translate → verify."""
    settings = get_settings()
    _setup_logging(log_level or settings.log_level)
    init_tracing()

    source = _read_source(source_file)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    src_lang = _source_language_from_path(source_file)

    console.print(Panel("[bold cyan]LegacyShift Migration Pipeline[/bold cyan]", expand=False))

    # Parse
    with console.status(f"[bold green]Parsing {src_lang} source..."):
        parser = get_parser(src_lang)
        parsed = parser.parse(source)

    if isinstance(parsed, CobolParsedCode):
        console.print(f"  [dim]Parsed COBOL program {parsed.program_id or '?'}, "
                      f"{parsed.method_count} paragraph(s)[/dim]")
    else:
        console.print(f"  [dim]Parsed {len(parsed.classes)} class(es), "
                      f"{sum(len(c.methods) for c in parsed.classes)} method(s)[/dim]")

    # Build and invoke graph
    graph = build_graph()
    max_iter = max_retries if max_retries is not None else settings.max_retries

    initial_state = {
        "source_code": source,
        "source_language": src_lang,
        "target_language": "python",
        "structure_summary": parsed.summary(),
        "iteration": 0,
        "max_iterations": max_iter,
    }

    with console.status("[bold green]Running migration pipeline (this may take a minute)..."):
        final_state = graph.invoke(initial_state)

    # Output results
    explanation = final_state.get("explanation", "")
    test_code = final_state.get("test_code", "")
    translated_code = final_state.get("translated_code", "")
    status = final_state.get("status", "unknown")
    iterations = final_state.get("iteration", 0)

    stem = Path(source_file).stem

    if explanation:
        (out / f"{stem}_explanation.md").write_text(explanation, encoding="utf-8")
    if test_code:
        (out / f"test_{stem}.py").write_text(test_code, encoding="utf-8")
    if translated_code:
        (out / f"{stem}.py").write_text(translated_code, encoding="utf-8")

    # Summary
    console.print()
    if status == "success":
        console.print(Panel(
            f"[bold green]Migration succeeded[/bold green] after {iterations} iteration(s).\n"
            f"All generated tests pass.",
            title="Result",
        ))
    elif status == "partial":
        console.print(Panel(
            f"[bold yellow]Partial migration[/bold yellow] — tests still failing after "
            f"{iterations} iteration(s).\nReview the output and fix remaining issues manually.",
            title="Result",
        ))
    else:
        console.print(Panel(
            f"[bold red]Migration failed[/bold red] — status: {status}",
            title="Result",
        ))

    console.print(f"\n  Output files written to [bold]{out.resolve()}[/bold]:")
    for f in sorted(out.glob(f"*{stem}*")):
        console.print(f"    {f.name}")


@main.command()
@click.argument("source_file")
@click.option("--model", "-m", default=None, help="LLM model to use.")
@click.option("--log-level", default=None, help="Log level.")
def explain(source_file: str, model: str | None, log_level: str | None) -> None:
    """Explain what a Java or COBOL source file does in plain English."""
    settings = get_settings()
    _setup_logging(log_level or settings.log_level)
    init_tracing()

    source = _read_source(source_file)
    src_lang = _source_language_from_path(source_file)

    with console.status("[bold green]Parsing..."):
        parser = get_parser(src_lang)
        parsed = parser.parse(source)

    from legacy_shift.graph.nodes import explain_node

    state = {
        "source_code": source,
        "source_language": src_lang,
        "structure_summary": parsed.summary(),
    }

    with console.status("[bold green]Generating explanation..."):
        result = explain_node(state)

    console.print()
    console.print(Markdown(result["explanation"]))


@main.command()
@click.argument("source_file")
@click.option("--output-dir", "-o", default=".", help="Directory to write test file.")
@click.option("--model", "-m", default=None, help="LLM model to use.")
@click.option("--log-level", default=None, help="Log level.")
def generate_tests(
    source_file: str, output_dir: str, model: str | None, log_level: str | None
) -> None:
    """Generate a pytest test suite for the Java or COBOL source (without translating)."""
    settings = get_settings()
    _setup_logging(log_level or settings.log_level)
    init_tracing()

    source = _read_source(source_file)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    src_lang = _source_language_from_path(source_file)

    with console.status("[bold green]Parsing..."):
        parser = get_parser(src_lang)
        parsed = parser.parse(source)

    from legacy_shift.graph.nodes import explain_node, test_gen_node

    state: dict = {
        "source_code": source,
        "source_language": src_lang,
        "structure_summary": parsed.summary(),
    }

    with console.status("[bold green]Generating explanation..."):
        state.update(explain_node(state))

    with console.status("[bold green]Generating tests..."):
        state.update(test_gen_node(state))

    test_code = state["test_code"]
    stem = Path(source_file).stem
    dest = out / f"test_{stem}.py"
    dest.write_text(test_code, encoding="utf-8")
    console.print(Syntax(test_code, "python", theme="monokai", line_numbers=True))
    console.print(f"\n  Test file written to [bold]{dest}[/bold]")
