#!/usr/bin/env python3
"""
DeMoD Sierpinski Beater v2.5 — Argent Metal Edition
96 BPM industrial metal preset + TUI preset selector
"""

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import pretty_midi
import soundfile as sf
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import questionary

VERSION = "2.5"
console = Console()

# ── Scale definitions ──────────────────────────────────────────────────────────

MODE_NAMES = [
    "Aeolian (dark)",
    "Dorian (modal)",
    "Phrygian (exotic)",
    "Mixolydian (bright rock)",
]

MODE_OFFSETS: List[List[int]] = [
    [0, 2, 3, 5, 7, 8, 10],  # Aeolian
    [0, 2, 3, 5, 7, 9, 10],  # Dorian
    [0, 1, 3, 5, 7, 8, 10],  # Phrygian
    [0, 2, 4, 5, 7, 9, 10],  # Mixolydian
]

PENTATONIC_BASE = [0, 3, 5, 7, 10]

# ── Velocity / duration constants ──────────────────────────────────────────────

VEL_KICK_METAL    = 115;  VEL_KICK_NORMAL    = 108
VEL_SNARE_METAL   = 105;  VEL_SNARE_NORMAL   =  98
VEL_HAT_STRONG    =  85;  VEL_HAT_NORMAL     =  78;  VEL_HAT_SOFT = 48
VEL_PAD_METAL     =  58;  VEL_PAD_NORMAL     =  52
VEL_BASS_ROOT     = 118;  VEL_BASS_ROOT_NORM = 112
VEL_BASS_STRONG   = 112;  VEL_BASS_MID       = 105;  VEL_BASS_SOFT = 88

DUR_KICK  = 0.12
DUR_SNARE = 0.15
DUR_HAT   = 0.06
DUR_BASS_ROOT_METAL  = 0.25;  DUR_BASS_ROOT_NORMAL = 0.95
DUR_BASS_RUN_METAL   = 0.18;  DUR_BASS_RUN_NORMAL  = 0.28

MIDI_KICK  = 36
MIDI_SNARE = 38
MIDI_HAT   = 42  # closed hi-hat
MIDI_RIDE  = 51  # ride bell

PROG_BASS = 33   # Electric Bass (finger)
PROG_PAD  = 89   # Pad 2 (warm)


# ── Config ─────────────────────────────────────────────────────────────────────

@dataclass
class SierpinskiConfig:
    mode: int        = 0
    bpm: float       = 120.0
    bars: int        = 64
    sf2_path: Optional[Path] = None
    output_base: str = "demod_sierpinski_beat"
    is_metal: bool   = False

    def apply_metal_preset(self) -> None:
        self.is_metal   = True
        self.mode       = 2          # Phrygian
        self.bpm        = 96.0
        self.bars       = 128
        self.output_base = "demod_sierpinski_argent_metal"

    def apply_standard_defaults(self) -> None:
        self.is_metal = False
        self.bpm      = 120.0
        self.bars     = 64


# ── SoundFont discovery ────────────────────────────────────────────────────────

def find_soundfonts() -> List[Path]:
    home = Path.home()
    search_dirs = [
        home / "SoundFonts",
        home / "Music" / "SoundFonts",
        home / "Downloads",
        Path("/usr/share/sounds/sf2"),
    ]
    candidates: List[Path] = []
    for d in search_dirs:
        if d.exists():
            candidates.extend(d.rglob("*.sf2"))
            candidates.extend(d.rglob("*.SF2"))
    return sorted(set(candidates))


def interactive_soundfont_loader() -> Optional[Path]:
    console.print("[bold cyan]🔍 Scanning for SoundFonts...[/]")
    sf2_list = find_soundfonts()

    if sf2_list:
        # Use index-stable mapping: label → Path, avoiding collisions from same filename
        labels = [f"{p.name}  ({p.parent})" for p in sf2_list]
        CUSTOM = "[Enter custom path]"
        choice = questionary.select("Select SoundFont:", choices=labels + [CUSTOM]).ask()
        if choice is None:
            return None
        if choice == CUSTOM:
            path_str = questionary.path("Full path to .sf2:").ask()
            if not path_str:
                return None
            sf2 = Path(path_str).expanduser().resolve()
        else:
            idx = labels.index(choice)
            sf2 = sf2_list[idx]
    else:
        path_str = questionary.path("Full path to .sf2 (blank for MIDI-only):").ask()
        if not path_str:
            return None
        sf2 = Path(path_str).expanduser().resolve()

    if sf2.exists() and sf2.suffix.lower() == ".sf2":
        console.print(f"[green]✓ Loaded {sf2.name}[/]")
        return sf2

    console.print("[red]Invalid path — file not found or not a .sf2[/]")
    return None


# ── Music generation ───────────────────────────────────────────────────────────

def get_chord(bar: int, mode: int, is_metal: bool) -> Tuple[int, List[int]]:
    """Return (root_pitch, [chord_tone_pitches]) for the given bar."""
    offsets    = MODE_OFFSETS[mode]
    root_base  = 40 if is_metal else 45  # E2 for metal, A2 otherwise
    pos        = bar % 4

    if pos < 2:  # i — tonic
        root  = root_base + offsets[0]
        # Degree indices: 1, 3, 5, 7 (or b6 for Phrygian which lacks a natural 7th feel)
        tone_idx = (0, 2, 4, 6 if mode != 2 else 5)
    elif pos == 2:  # III (or bVII in Mixolydian) — mediant
        root  = root_base + offsets[2]
        tone_idx = (2, 4, 6, 1 if mode == 3 else 0)
    else:  # V — dominant
        root  = root_base + offsets[4]
        # Fixed: was offsets[7] (OOB). Use 0 (root octave) as the 4th tone for non-Mixolydian.
        tone_idx = (4, 6, 1 if mode == 3 else 0, 3)

    tones = [root_base + offsets[i] for i in tone_idx]
    return root, tones


def is_sierpinski_hit(step: int, variation: int = 0) -> bool:
    """
    True when C(12 + variation, step) is odd — i.e. the cell is 'on' in Pascal's
    triangle mod 2, which generates the Sierpinski triangle fractal pattern.

    The old implementation OR'd in three bitwise checks that fired on 12–16 of 16
    steps (depending on variation), completely overwhelming the sparse fractal
    pattern. Pure Pascal mod 2 gives meaningful density variation: 1–16 hits per
    16 steps as variation cycles, which is exactly the fractal behaviour we want.
    """
    return (math.comb(12 + variation, step) % 2) == 1


def _quarter(bpm: float) -> float:
    """Duration of one quarter-note in seconds."""
    return 60.0 / bpm


def generate_midi(config: SierpinskiConfig) -> pretty_midi.PrettyMIDI:
    label = "Argent Metal fractal" if config.is_metal else "fractal"
    console.print(f"[bold green]Generating {label} MIDI — {config.bars} bars @ {config.bpm} BPM...[/]")

    midi = pretty_midi.PrettyMIDI(initial_tempo=config.bpm)
    drum = pretty_midi.Instrument(
        program=0, is_drum=True,
        name="DeMoD Argent Metal Drums" if config.is_metal else "DeMoD Fractal Drums",
    )
    bass = pretty_midi.Instrument(program=PROG_BASS, name="DeMoD Metal Bass")
    pad  = pretty_midi.Instrument(program=PROG_PAD,  name="DeMoD Sierpinski Pad")

    q = _quarter(config.bpm)
    pentatonic = [40 + o if config.is_metal else 45 + o for o in PENTATONIC_BASE]

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Building bars...", total=config.bars)

        for bar in range(config.bars):
            bar_start = bar * q * 4  # 4 quarter-notes per bar
            root, chord_tones = get_chord(bar, config.mode, config.is_metal)

            # Pad: sustained chord every other bar, spanning 2 bars
            if bar % 2 == 0:
                vel = VEL_PAD_METAL if config.is_metal else VEL_PAD_NORMAL
                for pitch in chord_tones:
                    pad.notes.append(pretty_midi.Note(
                        velocity=vel, pitch=pitch + 12,
                        start=bar_start, end=bar_start + q * 8,
                    ))

            for step in range(16):
                t = bar_start + step * (q / 4)  # 16th-note grid

                # Kick — on every beat, plus fractal doubles in metal
                if step % 4 == 0 or (config.is_metal and is_sierpinski_hit(step, bar % 4)):
                    vel = VEL_KICK_METAL if config.is_metal else VEL_KICK_NORMAL
                    drum.notes.append(pretty_midi.Note(velocity=vel, pitch=MIDI_KICK, start=t, end=t + DUR_KICK))

                # Snare — backbeat (steps 4 and 12 on 16th grid = beats 2&4) + fractal fills
                if step in (4, 12) or (step % 4 == 2 and is_sierpinski_hit(step, bar % 8)):
                    vel = VEL_SNARE_METAL if config.is_metal else VEL_SNARE_NORMAL
                    drum.notes.append(pretty_midi.Note(velocity=vel, pitch=MIDI_SNARE, start=t, end=t + DUR_SNARE))

                # Hi-hat / ride — fractal shimmer
                if is_sierpinski_hit(step, variation=bar % 7):
                    if config.is_metal:
                        vel = VEL_HAT_STRONG
                    elif step % 4 == 0:
                        vel = VEL_HAT_NORMAL
                    else:
                        vel = VEL_HAT_SOFT
                    hat_pitch = MIDI_RIDE if config.is_metal else MIDI_HAT
                    drum.notes.append(pretty_midi.Note(velocity=vel, pitch=hat_pitch, start=t, end=t + DUR_HAT))

                # Bass root — anchor on beat 1 of each bar
                if step == 0:
                    dur = DUR_BASS_ROOT_METAL if config.is_metal else DUR_BASS_ROOT_NORMAL
                    vel = VEL_BASS_ROOT if config.is_metal else VEL_BASS_ROOT_NORM
                    bass.notes.append(pretty_midi.Note(velocity=vel, pitch=root, start=t, end=t + dur))

                # Bass fractal runs — skip step 0 to avoid colliding with the root note above
                if step != 0 and is_sierpinski_hit(step, variation=bar % 5):
                    pitch = pentatonic[step % len(pentatonic)]
                    dur   = DUR_BASS_RUN_METAL if config.is_metal else DUR_BASS_RUN_NORMAL
                    if config.is_metal:
                        vel = VEL_BASS_STRONG
                    elif step % 8 == 0:
                        vel = VEL_BASS_MID
                    else:
                        vel = VEL_BASS_SOFT
                    bass.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=t, end=t + dur))

            progress.update(task, advance=1)

    midi.instruments.extend([drum, bass, pad])
    return midi


# ── WAV rendering ──────────────────────────────────────────────────────────────

def render_wav(midi: pretty_midi.PrettyMIDI, sf2_path: Path, output_base: str) -> None:
    wav_path = Path(f"{output_base}.wav")
    console.print("[bold cyan]Rendering WAV with FluidSynth (this may take a moment)...[/]")
    try:
        audio = midi.fluidsynth(sf2_path=str(sf2_path), fs=44100)
        sf.write(str(wav_path), audio, 44100, subtype="PCM_24")
        console.print(f"[green]✓ WAV saved → {wav_path}[/]")
    except Exception as e:
        console.print(f"[red]WAV render failed: {e}[/]")


# ── TUI ────────────────────────────────────────────────────────────────────────

def show_banner() -> None:
    console.print(Panel(
        f"[bold magenta]DeMoD SIERPINSKI BEATER v{VERSION} — ARGENT METAL EDITION\n"
        "[dim]96 BPM Industrial Metal · Fractal Rhythm Engine[/]",
        style="bold magenta",
        expand=False,
    ))


def _ask(prompt_fn):
    """Wrap a questionary call; return None and print a warning if the user aborts."""
    result = prompt_fn()
    if result is None:
        console.print("[yellow]Cancelled.[/]")
    return result


def main_tui() -> None:
    config = SierpinskiConfig()

    while True:
        show_banner()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold cyan]1.[/]", "Standard Modes")
        table.add_row("[bold cyan]2.[/]", "Argent Metal Preset (96 BPM, E Phrygian, 128 bars)")
        table.add_row("[bold cyan]3.[/]", "Load SoundFont")
        table.add_row("[bold cyan]4.[/]", "Set Output Name")
        table.add_row("[bold cyan]5.[/]", "[bold green]GENERATE[/]")
        table.add_row("[bold cyan]6.[/]", "Exit")
        console.print(table)

        # Show current config inline
        sf_label = config.sf2_path.name if config.sf2_path else "[dim]none — MIDI only[/]"
        console.print(
            f"[dim]Current: {config.bpm} BPM · {MODE_NAMES[config.mode]} · "
            f"{'Metal ⚡' if config.is_metal else 'Standard'} · "
            f"{config.bars} bars · sf2={sf_label}[/]"
        )

        choice = _ask(lambda: questionary.select(
            "Choose:", choices=["1", "2", "3", "4", "5", "6"],
        ).ask())
        if choice is None:
            break

        if choice == "1":
            mode_str = _ask(lambda: questionary.select(
                "Mode:", choices=[f"{i} - {n}" for i, n in enumerate(MODE_NAMES)],
            ).ask())
            if mode_str is None:
                continue
            config.mode = int(mode_str.split(" - ")[0])
            config.apply_standard_defaults()

        elif choice == "2":
            config.apply_metal_preset()
            console.print("[bold red]⚡ ARGENT METAL PRESET LOADED — 96 BPM E Phrygian · 128 bars[/]")

        elif choice == "3":
            config.sf2_path = interactive_soundfont_loader()

        elif choice == "4":
            name = _ask(lambda: questionary.text(
                "Output base name:", default=config.output_base,
            ).ask())
            if name:
                config.output_base = name

        elif choice == "5":
            console.print(Panel(
                f"[bold cyan]BPM:[/] {config.bpm}  "
                f"[bold cyan]Mode:[/] {MODE_NAMES[config.mode]}  "
                f"[bold cyan]Metal:[/] {config.is_metal}  "
                f"[bold cyan]Bars:[/] {config.bars}  "
                f"[bold cyan]SoundFont:[/] {sf_label}"
            ))
            confirmed = _ask(lambda: questionary.confirm("Generate now?").ask())
            if not confirmed:
                continue

            midi      = generate_midi(config)
            midi_path = Path(f"{config.output_base}.mid")
            midi.write(str(midi_path))
            console.print(f"[green]✓ MIDI saved → {midi_path}[/]")

            if config.sf2_path:
                render_wav(midi, config.sf2_path, config.output_base)

            console.print("[bold green]🎸 Fractal metal unleashed.[/]")

            again = _ask(lambda: questionary.confirm("Generate another?").ask())
            if not again:
                break

        elif choice == "6":
            console.print("[bold]👋 Argent Metal session complete.[/]")
            break


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="demod-sierpinski",
        description=f"DeMoD Sierpinski Beater v{VERSION} — fractal MIDI/WAV generator",
    )
    p.add_argument("--metal",   action="store_true",       help="Use Argent Metal preset (96 BPM, E Phrygian, 128 bars)")
    p.add_argument("--mode",    type=int, default=0,        help="Scale mode 0–3 (Aeolian/Dorian/Phrygian/Mixolydian)")
    p.add_argument("--bpm",     type=float, default=120.0,  help="Tempo in BPM")
    p.add_argument("--bars",    type=int, default=64,       help="Number of bars to generate")
    p.add_argument("--sf2",     type=Path, default=None,    help="Path to a .sf2 SoundFont for WAV render")
    p.add_argument("--out",     type=str,  default="demod_sierpinski_beat", help="Output file base name")
    return p


def main() -> None:
    if len(sys.argv) > 1:
        parser = build_cli_parser()
        args   = parser.parse_args()

        config = SierpinskiConfig()
        if args.metal:
            config.apply_metal_preset()
        else:
            if not (0 <= args.mode <= 3):
                parser.error("--mode must be 0–3")
            config.mode = args.mode
            config.bpm  = args.bpm
            config.bars = args.bars

        if args.sf2:
            sf2 = args.sf2.expanduser().resolve()
            if not sf2.exists() or sf2.suffix.lower() != ".sf2":
                parser.error(f"Invalid SoundFont path: {sf2}")
            config.sf2_path = sf2

        config.output_base = args.out

        console.print(f"[bold magenta]DeMoD Sierpinski Beater v{VERSION}[/]")
        midi      = generate_midi(config)
        midi_path = Path(f"{config.output_base}.mid")
        midi.write(str(midi_path))
        console.print(f"[green]✓ MIDI saved → {midi_path}[/]")
        if config.sf2_path:
            render_wav(midi, config.sf2_path, config.output_base)
    else:
        try:
            main_tui()
        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted.[/]")


if __name__ == "__main__":
    main()
