#!/usr/bin/env python3
"""
StarTUI - Interactive terminal tool for generating star trail images,
star trail videos, and timelapses from a folder of sequential photos.
"""

import sys
import time
import multiprocessing as mp
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from core.star_trail import generate_star_trail
from core.timelapse import generate_timelapse
from core.trail_video import generate_trail_video
from core.video_writer import output_frame_count

console = Console()

DURATION_CHOICES = ["5", "10", "15"]
RESOLUTION_CHOICES = {"720p": 720, "1080p": 1080, "Original": None}
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")


def banner():
    console.print(
        Panel.fit(
            "[bold cyan]StarTUI[/bold cyan]\n"
            "[dim]Star trails & timelapses from your night sky photos[/dim]",
            border_style="cyan",
        )
    )


def get_images(folder):
    return sorted(Path(folder).glob("*.jpg"))


def worker(func, images, out_path, extra_args, queue, label):
    """Runs one generation job in its own process, reporting progress via queue."""

    def cb(done, total):
        queue.put((label, done))

    func(images, out_path, *extra_args, progress_callback=cb)
    queue.put((label, "DONE"))


def main():
    banner()

    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        console.print(f"[red]Input folder '{INPUT_DIR}/' not found.[/red]")
        console.print(f"[dim]Create it and add your .jpg frames, then run again.[/dim]")
        sys.exit(1)

    folder = INPUT_DIR
    images = get_images(folder)

    if not images:
        console.print(f"[red]No .jpg files found in '{INPUT_DIR}/'.[/red]")
        sys.exit(1)

    outputs = questionary.checkbox(
        "Select outputs to generate:",
        choices=[
            questionary.Choice("Star Trail Image", value="image"),
            questionary.Choice("Star Trail Video", value="trail_video"),
            questionary.Choice("Timelapse", value="timelapse"),
        ],
    ).ask()
    if not outputs:
        console.print("[yellow]No outputs selected. Exiting.[/yellow]")
        sys.exit(0)

    duration = None
    target_height = None
    if "trail_video" in outputs or "timelapse" in outputs:
        duration = int(
            questionary.select(
                "Video duration (seconds):",
                choices=DURATION_CHOICES,
                default="5",
            ).ask()
        )
        resolution = questionary.select(
            "Video resolution (aspect ratio preserved):",
            choices=list(RESOLUTION_CHOICES.keys()),
            default="1080p",
        ).ask()
        target_height = RESOLUTION_CHOICES[resolution]

    table = Table(title="Job Summary", show_header=False, border_style="cyan")
    table.add_row("Input folder", str(folder))
    table.add_row("Frames found", str(len(images)))
    table.add_row("Outputs", ", ".join(outputs))
    if duration:
        table.add_row("Duration", f"{duration}s")
        table.add_row("Resolution", resolution)
    console.print(table)

    if not questionary.confirm("Proceed?", default=True).ask():
        console.print("[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    OUTPUT_DIR.mkdir(exist_ok=True)

    jobs = []
    if "image" in outputs:
        jobs.append(("Star Trail Image", generate_star_trail, OUTPUT_DIR / "startrail.jpg", (), len(images)))
    if "trail_video" in outputs:
        video_frames = output_frame_count(duration)
        jobs.append(("Star Trail Video", generate_trail_video, OUTPUT_DIR / "trail_timelapse.mp4", (duration, target_height), video_frames))
    if "timelapse" in outputs:
        video_frames = output_frame_count(duration)
        jobs.append(("Timelapse", generate_timelapse, OUTPUT_DIR / "timelapse.mp4", (duration, target_height), video_frames))

    start_total = time.time()

    progress_columns = (
        TextColumn("[bold blue]{task.fields[label]}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} frames"),
        TimeRemainingColumn(),
    )

    queue = mp.Queue()
    processes = []
    task_ids = {}
    task_totals = {}

    with Progress(*progress_columns, console=console) as progress:

        for label, func, out_path, extra_args, total in jobs:
            task_ids[label] = progress.add_task("", total=total, label=label)
            task_totals[label] = total
            p = mp.Process(target=worker, args=(func, images, out_path, extra_args, queue, label))
            processes.append(p)
            p.start()

        finished = set()
        while len(finished) < len(jobs):
            label, value = queue.get()
            if value == "DONE":
                finished.add(label)
                progress.update(task_ids[label], completed=task_totals[label])
            else:
                progress.update(task_ids[label], completed=value)

        for p in processes:
            p.join()

    results = [out_path for _, _, out_path, _, _ in jobs]
    elapsed = time.time() - start_total

    console.print()
    console.print(
        Panel.fit(
            "\n".join(f"[green]\u2713[/green] {p}" for p in results)
            + f"\n\n[dim]Done in {elapsed:.1f}s[/dim]",
            title="[bold green]Complete[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()