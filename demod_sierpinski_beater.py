#!/usr/bin/env python3
"""
DeMoD Sierpinski Beater v2.4 — Argent Metal Edition
96 BPM industrial metal preset + TUI preset selector
"""

import argparse
import math
import sys
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import pretty_midi
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import questionary

VERSION = "2.4"
console = Console()

class SierpinskiConfig:
    def __init__(self):
        self.mode: int = 0
        self.bpm: float = 120.0
        self.bars: int = 64
        self.sf2_path: Optional[Path] = None
        self.output_base: str = "demod_sierpinski_beat"
        self.is_metal: bool = False  # Argent Metal flag

MODE_NAMES = ["Aeolian (dark)", "Dorian (modal)", "Phrygian (exotic)", "Mixolydian (bright rock)"]

MODE_OFFSETS = [
    [0, 2, 3, 5, 7, 8, 10],   # Aeolian
    [0, 2, 3, 5, 7, 9, 10],   # Dorian
    [0, 1, 3, 5, 7, 8, 10],   # Phrygian
    [0, 2, 4, 5, 7, 9, 10]    # Mixolydian
]

PENTATONIC_BASE = [0, 3, 5, 7, 10]

def find_soundfonts() -> List[Path]:
    home = Path.home()
    dirs = [home / "SoundFonts", home / "Music" / "SoundFonts", home / "Downloads", Path("/usr/share/sounds/sf2")]
    candidates = []
    for d in dirs:
        if d.exists():
            candidates.extend(list(d.rglob("*.sf2")) + list(d.rglob("*.SF2")))
    return sorted(set(candidates))

def interactive_soundfont_loader() -> Optional[Path]:
    console.print("[bold cyan]🔍 Scanning for SoundFonts...[/]")
    sf2_list = find_soundfonts()
    if sf2_list:
        choices = [f"{p.name} ({p.parent})" for p in sf2_list] + ["[Enter custom path]"]
        selected = questionary.select("Select SoundFont:", choices=choices).ask()
        if selected == "[Enter custom path]":
            path_str = questionary.path("Full path to .sf2:").ask()
            sf2 = Path(path_str).expanduser().resolve()
        else:
            sf2 = sf2_list[choices.index(selected)]
    else:
        path_str = questionary.path("Full path to .sf2 (blank for MIDI-only):").ask()
        if not path_str: return None
        sf2 = Path(path_str).expanduser().resolve()
    if sf2.exists() and sf2.suffix.lower() == ".sf2":
        console.print(f"[green]✓ Loaded {sf2.name}[/]")
        return sf2
    console.print("[red]Invalid path[/]")
    return None

def get_chord(bar: int, mode: int, is_metal: bool) -> Tuple[int, List[int]]:
    offsets = MODE_OFFSETS[mode]
    root_base = 40 if is_metal else 45  # E2 for metal, A2 otherwise
    pos = bar % 4
    if pos < 2:  # i
        root = root_base + offsets[0]
        tones = [root_base + offsets[i] for i in (0, 2, 4, 6 if mode != 2 else 5)]
        return root, tones
    elif pos == 2:
        root = root_base + offsets[2]
        tones = [root_base + offsets[i] for i in (2, 4, 6, 1 if mode == 3 else 0)]
        return root, tones
    else:
        root = root_base + offsets[4]
        tones = [root_base + offsets[i] for i in (4, 6, 1 if mode == 3 else 7, 3)]
        return root, tones

def is_sierpinski_hit(step: int, variation: int = 0) -> bool:
    pascal = (math.comb(12 + variation, step) % 2) == 1
    bitwise = ((step & (step >> 1)) == 0) or ((step & (step >> 2)) == 0) or ((step & (step >> 3)) == 0)
    return pascal or bitwise

def generate_midi(config: SierpinskiConfig) -> pretty_midi.PrettyMIDI:
    console.print("[bold green]Generating Argent Metal fractal MIDI...[/]" if config.is_metal else "[bold green]Generating fractal MIDI...[/]")
    midi = pretty_midi.PrettyMIDI(initial_tempo=config.bpm)
    drum = pretty_midi.Instrument(program=0, is_drum=True, name="DeMoD Argent Metal Drums" if config.is_metal else "DeMoD Fractal Drums")
    bass = pretty_midi.Instrument(program=33, name="DeMoD Metal Bass")
    pad = pretty_midi.Instrument(program=89, name="DeMoD Sierpinski Pad")

    pentatonic = [40 + o if config.is_metal else 45 + o for o in PENTATONIC_BASE]

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Building bars...", total=config.bars)
        for bar in range(config.bars):
            start_time = bar * (60.0 / config.bpm * 4)
            root, chord_tones = get_chord(bar, config.mode, config.is_metal)

            if bar % 2 == 0:
                for note in chord_tones:
                    n = pretty_midi.Note(velocity=58 if config.is_metal else 52, pitch=note + 12,
                                         start=start_time, end=start_time + (60.0 / config.bpm * 8))
                    pad.notes.append(n)

            for step in range(16):
                t = start_time + step * (60.0 / config.bpm / 4)

                # Kick — double-kick feel in metal
                if step % 4 == 0 or (config.is_metal and is_sierpinski_hit(step, bar % 4)):
                    vel = 115 if config.is_metal else 108
                    drum.notes.append(pretty_midi.Note(velocity=vel, pitch=36, start=t, end=t + 0.12))

                # Snare
                if (step in (6, 14)) or (step % 4 == 2 and is_sierpinski_hit(step, bar % 8)):
                    drum.notes.append(pretty_midi.Note(velocity=105 if config.is_metal else 98, pitch=38, start=t, end=t + 0.15))

                # Hi-hat / ride (metal shimmer)
                if is_sierpinski_hit(step, variation=bar % 7):
                    vel = 85 if config.is_metal else 78 if step % 4 == 0 else 48
                    drum.notes.append(pretty_midi.Note(velocity=vel, pitch=42 if not config.is_metal else 51, start=t, end=t + 0.06))

                # Bass — palm-mute short notes in metal
                if step == 0:
                    bass.notes.append(pretty_midi.Note(velocity=118 if config.is_metal else 112, pitch=root, start=t, end=t + (0.25 if config.is_metal else 0.95)))

                if is_sierpinski_hit(step, variation=bar % 5):
                    pitch = pentatonic[step % len(pentatonic)]
                    dur = 0.18 if config.is_metal else 0.28
                    vel = 112 if config.is_metal else 105 if step % 8 == 0 else 88
                    bass.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + dur))

            progress.update(task, advance=1)

    midi.instruments.extend([drum, bass, pad])
    return midi

def render_wav(midi: pretty_midi.PrettyMIDI, sf2_path: Path, output_base: str):
    console.print("[bold cyan]Rendering WAV with FluidSynth...[/]")
    wav_path = Path(f"{output_base}.wav")
    try:
        with Progress() as progress:
            task = progress.add_task("Rendering...", total=100)
            audio = midi.fluidsynth(sf2_path=str(sf2_path), fs=44100)
            progress.update(task, completed=50)
            import soundfile as sf
            sf.write(str(wav_path), audio, 44100, subtype='PCM_24')
            progress.update(task, completed=100)
        console.print(f"[green]✓ WAV saved → {wav_path}[/]")
    except Exception as e:
        console.print(f"[red]WAV failed: {e}[/]")

def show_banner():
    console.print(Panel(f"""
[bold magenta]╔════════════════════════════════════════════════════════════╗
║           DeMoD SIERPINSKI BEATER v{VERSION} — ARGENT METAL          ║
║               96 BPM Industrial Metal Preset Ready                 ║
╚════════════════════════════════════════════════════════════╝[/]
""", style="bold magenta", expand=False))

def main_tui():
    config = SierpinskiConfig()
    while True:
        show_banner()
        table = Table(show_header=False)
        table.add_row("1.", "Standard Modes")
        table.add_row("2.", "Argent Metal Preset (96 BPM)")
        table.add_row("3.", "Load SoundFont")
        table.add_row("4.", "Set Output Name")
        table.add_row("5.", "[bold green]GENERATE[/]")
        table.add_row("6.", "Exit")
        console.print(table)

        choice = questionary.select("Choose:", choices=["1","2","3","4","5","6"]).ask()

        if choice == "1":
            config.mode = int(questionary.select("Mode:", [f"{i} - {n}" for i,n in enumerate(MODE_NAMES)]).ask().split(" - ")[0])
            config.bpm = 120.0
            config.is_metal = False

        elif choice == "2":
            config.is_metal = True
            config.mode = 2  # Phrygian
            config.bpm = 96.0
            config.bars = 128
            config.output_base = "demod_sierpinski_argent_metal"
            console.print("[bold red]ARGENT METAL PRESET LOADED — 96 BPM E Phrygian[/]")

        elif choice == "3":
            config.sf2_path = interactive_soundfont_loader()

        elif choice == "4":
            config.output_base = questionary.text("Output base:", default=config.output_base).ask()

        elif choice == "5":
            console.print(Panel(f"[bold cyan]Config:\nBPM: {config.bpm} | Mode: {MODE_NAMES[config.mode]} | Metal: {config.is_metal} | Bars: {config.bars}[/]"))
            if questionary.confirm("Generate now?").ask():
                midi = generate_midi(config)
                midi_path = Path(f"{config.output_base}.mid")
                midi.write(str(midi_path))
                console.print(f"[green]✓ MIDI saved → {midi_path}[/]")
                if config.sf2_path:
                    render_wav(midi, config.sf2_path, config.output_base)
                console.print("[bold green]🎸 Plug in your bass and unleash the fractal metal![/]")
                if not questionary.confirm("Generate another?").ask():
                    break

        elif choice == "6":
            console.print("[bold]👋 Argent Metal session complete![/]")
            break

def main():
    console.print("[bold magenta]DeMoD Sierpinski Beater v2.4 — Argent Metal Edition[/]")
    cli_config = None  # CLI fallback omitted for brevity in this file — same as v2.3
    if len(sys.argv) > 1:
        # (CLI parser unchanged from v2.3)
        pass
    else:
        try:
            main_tui()
        except KeyboardInterrupt:
            console.print("\n[bold red]Cancelled[/]")

if __name__ == "__main__":
    main()