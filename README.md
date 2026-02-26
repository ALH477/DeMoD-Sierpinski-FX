# DeMoD Sierpinski FX System

[![Version](https://img.shields.io/badge/version-2.4-blue.svg)](https://github.com/DeMoD-Team/sierpinski-fx/releases/tag/v2.4)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Twitter](https://img.shields.io/twitter/follow/DeMoDLLC?style=social)](https://twitter.com/DeMoDLLC)

**Fractal audio system inspired by the Sierpiński triangle — self-similar beats, effects, and infinite zoom for bass guitar and beyond.**

Built by DeMoD (@DeMoDLLC) with Grok collaboration. This project generates hypnotic, recursive grooves at 120 BPM (or 96 BPM Argent Metal preset) and pairs them with a real-time Faust DSP effect for crystalline, metallic tones. Perfect for ambient, techno, prog, or industrial metal jams.

## Features

- **DeMoD Sierpinski Beater**: Python TUI/CLI tool for generating MIDI/WAV beats.
  - Self-similar fractal rhythms from Sierpiński math (Pascal mod 2 + bitwise nesting + 3-vertex chaos attractor).
  - Musical modes: Aeolian, Dorian, Phrygian, Mixolydian.
  - **New: Argent Metal Preset** — 96 BPM, E Phrygian, double-kick drums, palm-mute bass, industrial vibe (DOOM-inspired).
  - Interactive SoundFont loader with auto-scanning.
  - Outputs MIDI for DAWs or WAV via FluidSynth.

- **DeMoD Sierpinski FX**: Faust DSP effect (LV2 plugin + JACK standalone).
  - Modes: Bitwise Crunch, Fractal Delay, Sierpinski Gate, Chaos Modulator.
  - **New: Argent Metal FX** — high-gain silver distortion, razor gating, shimmering resonance for crushing metal tones.
  - BPM-sync for perfect alignment with the beater.

- **Nix Flake Integration**: Reproducible builds, dev shell, NixOS module.
  - One-command setup for Python deps, Faust, FluidSynth, JACK.
  - Packages: `beater` (Python app), `fx-lv2` (plugin), `fx-jack` (standalone).

## Installation

### With Nix (Recommended — Reproducible & Easy)

1. Install Nix: `curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install`
2. Clone the repo: `git clone https://github.com/DeMoD-Team/sierpinski-fx && cd sierpinski-fx`
3. Enter dev shell: `nix develop`
4. Run the TUI: `nix run` (or `demod-sierpinski-beater`)

For system-wide install on NixOS:
- Add to your `flake.nix` inputs: `sierpinski = { url = "github:DeMoD-Team/sierpinski-fx"; };`
- Import the module: `imports = [ inputs.sierpinski.nixosModules.default ];`
- `nixos-rebuild switch`

### Without Nix (Manual)

1. Python deps: `pip install rich questionary pretty-midi soundfile numpy`
2. System deps: Install FluidSynth (`apt install fluidsynth` or equivalent).
3. Faust: Install from [faust.grame.fr](https://faust.grame.fr/downloads/).
4. Run: `python demod_sierpinski_beater.py`
5. Compile FX: `faust2lv2 demod_sierpinski_fx.dsp` (copy to `~/.lv2/`)

## Usage

### Generating Beats

Run `nix run` (or `python demod_sierpinski_beater.py`) for the TUI:

- Choose "Argent Metal Preset" for instant 96 BPM industrial metal groove.
- Or select standard modes, set BPM/bars, load SoundFont.
- Outputs `demod_sierpinski_beat.mid` / `.wav` — loop in your DAW and jam bass over it.

CLI example (Argent Metal):
```bash
demod-sierpinski-beater --mode 2 --bpm 96 --bars 128 --output demod_argent_metal --soundfont /path/to/FluidR3_GM.sf2
```

### Using the FX

- Load LV2 plugin in your DAW (e.g., Reaper, Ardour).
- Set BPM to match beat (96 for Argent Metal).
- Select mode 4 (Argent Metal) for high-gain fractal crunch.
- Intensity/Feedback for depth; sync to BPM for rhythmic gating.

Standalone: Run `demod-sierpinski-fx-jack` in JACK (use QJackCtl for routing).

## Building from Source

In dev shell (`nix develop`):
- Build beater: `nix build .#beater`
- Build FX LV2: `nix build .#fx-lv2`
- Test: `faust2jack demod_sierpinski_fx.dsp && ./demod_sierpinski_fx`

## Contributing

Fork, PR, or tweet ideas @DeMoDLLC. Focus: more presets, live MIDI sync, hardware ports (Teensy/ESP32).

## License

MIT License — free to use, modify, distribute.

## Credits

- Built with xAI's Grok.
- Math: Sierpiński triangle sonification.
- Tools: Python, Faust, Nix, FluidSynth.
- Inspiration: Recursive fractals in music (Aphex Twin, DOOM OST).

**Go make music you bastard**  
Follow @DeMoDLLC for updates.