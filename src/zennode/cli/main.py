import datetime
import os
import subprocess
import uuid

import structlog
import typer
from rich.console import Console
from rich.panel import Panel

from zennode.infrastructure.config import Config
from zennode.workflows.graph import pipeline_graph

app = typer.Typer(
    name="audhd-pipeline",
    help="Enterprise-Grade AuDHD Pedagogical Pipeline for deeply structured learning."
)
console = Console()
logger = structlog.get_logger(__name__)

def notify_mac(title: str, message: str) -> None:
    """Uses macOS osascript to send a native notification."""
    try:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception as e:
        logger.warning("failed_to_send_mac_notification", error=str(e))

@app.command()
def process(
    obsidian_file: str = typer.Argument(..., help="Path to the Obsidian markdown file containing your dumped context (links, text, images)."),
    audio_file: str = typer.Option(None, "--audio", "-a", help="Optional path to the voice dump audio recording.")
) -> None:
    """
    Executes the Feynman Technique Study Pipeline.
    Reads context, transcribes audio, performs a first-principles reality check, and synthesizes the Mastery Sheet.
    """
    console.print(Panel(f"[bold blue]Starting AuDHD Synthesis Pipeline[/bold blue]\nTarget: {obsidian_file}"))
    
    if obsidian_file.lower().endswith(('.m4a', '.mp3', '.webm', '.ogg', '.wav')):
        console.print("\n[bold yellow]Wait! This is an audio file, not an Obsidian Markdown file![/bold yellow]")
        console.print("The pipeline needs an Obsidian Note to append the Mastery Sheet to.")
        console.print("To use a raw audio file, create a new note (e.g. Concept.md), embed the audio inside it `![[Recording.m4a]]` and run:\n")
        console.print("[bold cyan]uv run audhd-pipeline Concept.md[/bold cyan]\n")
        raise typer.Exit(code=1)
    
    if not os.path.exists(obsidian_file):
        # Try resolving via OBSIDIAN_STUDY_DUMPS_PATH
        dumps_dir = os.environ.get("OBSIDIAN_STUDY_DUMPS_PATH")
        if dumps_dir:
            candidate = os.path.join(dumps_dir, obsidian_file)
            if os.path.exists(candidate):
                obsidian_file = candidate

    if not os.path.exists(obsidian_file):
        # Try resolving via OBSIDIAN_VAULT_PATH
        try:
            vault_dir = Config.get_obsidian_vault_path()
            candidate = os.path.join(vault_dir, obsidian_file)
            if os.path.exists(candidate):
                obsidian_file = candidate
        except ValueError:
            pass

    if not os.path.exists(obsidian_file):
        console.print(f"[bold red]Error:[/bold red] Obsidian file not found at {obsidian_file}")
        raise typer.Exit(code=1)
        
    if audio_file and not os.path.exists(audio_file):
        console.print(f"[bold red]Error:[/bold red] Audio file not found at {audio_file}")
        raise typer.Exit(code=1)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "obsidian_file_path": obsidian_file,
        "audio_file_path": audio_file,
    }

    try:
        with console.status("[bold green]Agentic Pipeline Running... (Parsing -> Transcribing -> Reality Checking -> Synthesizing)[/bold green]"):
            # Stream the events to show progress
            for event in pipeline_graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, _node_output in event.items():
                    console.print(f"[green]✓ Completed Node:[/green] {node_name}")
                    
        console.print(Panel("[bold green]Pipeline Complete! Mastery Sheet appended to your Obsidian Vault.[/bold green]"))
        notify_mac("AuDHD Pipeline Complete ✅", "Mastery Sheet appended to Obsidian Vault.")
    except Exception as e:
        logger.exception("pipeline_failed")
        console.print(Panel(f"[bold red]Pipeline Failed![/bold red]\n{str(e)}"))
        notify_mac("AuDHD Pipeline Failed ❌", str(e).replace('"', "'"))
        raise typer.Exit(code=1) from e

@app.command()
def start_menubar() -> None:
    """
    Starts the Zero-Friction macOS Menu Bar App (rumps).
    """
    console.print(Panel("[bold green]Starting AuDHD Menu Bar App...[/bold green] (Check your Mac menu bar!)"))
    from zennode.infrastructure.permissions import check_and_request_microphone_permission
    if not check_and_request_microphone_permission():
        console.print("[bold red]Error:[/bold red] Microphone permission is required for the AuDHD Pipeline Menu Bar app.")
        notify_mac("AuDHD Pipeline Failed ❌", "Microphone access denied.")
        raise typer.Exit(code=1)
        
    from zennode.app.menubar import main as run_menubar
    run_menubar()

@app.command()
def process_dump(
    dump_dir: str = typer.Argument(..., help="Path to the OpenViking Context folder containing audio and clipboard data.")
) -> None:
    """
    Processes a Zero-Friction Daily Dump.
    Creates the Infinite Daily Log file in your Obsidian vault and triggers the pipeline.
    """
    console.print(Panel(f"[bold blue]Processing Context Dump:[/bold blue]\n{dump_dir}"))
    if not os.path.exists(dump_dir):
        console.print(f"[bold red]Error:[/bold red] Dump directory not found at {dump_dir}")
        raise typer.Exit(code=1)
        
    vault_dir = Config.get_obsidian_vault_path()
    os.makedirs(vault_dir, exist_ok=True)
    
    # Define the Daily Log target
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    daily_log_path = os.path.join(vault_dir, f"Brain_Dump_{today_str}.md")
    
    # Touch the file if it doesn't exist
    if not os.path.exists(daily_log_path):
        with open(daily_log_path, "w", encoding="utf-8") as f:
            f.write(f"# 🧠 Brain Dump: {today_str}\n\n")
            f.write("> *Daily Context automatically ingested via AuDHD Menu Bar App.*\n\n---\n\n")
            
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "dump_dir": dump_dir,
        "obsidian_file_path": daily_log_path,
        "audio_file_path": None, # Will be resolved in ingest node if exists in dump_dir
    }

    try:
        with console.status("[bold green]Agentic Pipeline Running... (Parsing -> Transcribing -> Reality Checking -> Synthesizing)[/bold green]"):
            for event in pipeline_graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, _node_output in event.items():
                    console.print(f"[green]✓ Completed Node:[/green] {node_name}")
                    
        console.print(Panel(f"[bold green]Dump Complete! Synced to {daily_log_path}[/bold green]"))
        notify_mac("AuDHD Dump Complete ✅", "Daily Log has been updated.")
    except Exception as e:
        logger.exception("pipeline_failed")
        console.print(Panel(f"[bold red]Pipeline Failed![/bold red]\n{str(e)}"))
        notify_mac("AuDHD Dump Failed ❌", str(e).replace('"', "'"))
        raise typer.Exit(code=1) from e

@app.command()
def setup() -> None:
    """
    Zero-to-OSS Onboarding Wizard.
    Interactively guides the user to set up required API keys and directory paths, saving them to ~/.audhd/.env.
    """
    from pathlib import Path

    from rich.prompt import Prompt
    
    console.print(Panel("[bold cyan]Welcome to the AuDHD Pipeline Setup Wizard![/bold cyan]\nLet's get your environment configured. Press Enter to keep existing values."))
    
    global_env_dir = Path.home() / ".audhd"
    global_env_dir.mkdir(parents=True, exist_ok=True)
    env_file = global_env_dir / ".env"
    
    # Load existing to provide defaults
    existing_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    existing_vars[k] = v.strip("'\"")

    def ask(key: str, prompt_text: str, default_val: str = "") -> str:
        current = existing_vars.get(key, os.environ.get(key, default_val))
        return Prompt.ask(prompt_text, default=current)

    groq_key = ask("GROQ_API_KEY", "Enter your Groq API Key (for transcription & fast text fallback)")
    gemini_key = ask("GEMINI_API_KEY", "Enter your Gemini API Key (for vision & reality check)")
    openrouter_key = ask("OPENROUTER_API_KEY", "Enter your OpenRouter API Key (optional fallback)", default_val="sk-or-...")
    obsidian_path = ask("OBSIDIAN_VAULT_PATH", "Enter the absolute path to your Obsidian Vault")
    inbox_path = ask("AUDHD_INBOX_PATH", "Enter the absolute path for your Raw Capture _Inbox", default_val=str(Path.home() / "Documents" / "AuDHD_Inbox"))

    # Write to .env
    with open(env_file, "w") as f:
        f.write(f'GROQ_API_KEY="{groq_key}"\n')
        f.write(f'GEMINI_API_KEY="{gemini_key}"\n')
        f.write(f'OPENROUTER_API_KEY="{openrouter_key}"\n')
        f.write(f'OBSIDIAN_VAULT_PATH="{obsidian_path}"\n')
        f.write(f'AUDHD_INBOX_PATH="{inbox_path}"\n')
        
    console.print(Panel(f"[bold green]Setup Complete![/bold green]\nConfiguration saved securely to {env_file}"))

if __name__ == "__main__":
    app()
