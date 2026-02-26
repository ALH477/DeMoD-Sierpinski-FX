declare name "DeMoD Sierpinski FX";
declare author "DeMoD + Grok";
declare version "2.4";
declare description "Argent Metal Edition — 96 BPM industrial metal fractal effect";

import("stdfaust.lib");

process = vgroup("DeMoD Sierpinski FX v2.4 Argent Metal", 
    bypass * (dry * _ + wet * fx) : *(master_gain)
)
with {
    bypass = checkbox("[0] Bypass") : si.smoo;
    drywet = hslider("[1] Dry/Wet", 0.72, 0, 1, 0.01);
    intensity = hslider("[2] Intensity", 0.85, 0, 1, 0.01);
    feedback = hslider("[3] Feedback", 0.52, 0, 0.98, 0.01);
    bpm = hslider("[4] BPM [unit:BPM]", 96, 60, 180, 1);
    master_gain = hslider("[5] Master Gain [unit:dB]", 3, -12, 12, 0.1) : ba.db2linear;
    mode = hslider("[6] FX Mode [style:menu{'Bitwise Crunch':0;'Fractal Delay':1;'Sierpinski Gate':2;'Chaos Mod':3;'Argent Metal':4}]", 4, 0, 4, 1) : int;

    dry = 1 - drywet;
    wet = drywet;

    step = (os.phasor((bpm/60.0)*16.0, 0) * 65536) : int;
    sier_gate(d) = ((step & (step >> int(d))) == 0) : si.smoo : max(0.01);

    del_times = (0.25, 0.333, 0.5, 0.666, 0.75, 1.0);
    fractal_delay(x) = x <: par(i,6, de.fdelay(1.8*ma.SR, del_times(i)*ma.SR) * sier_gate(i+3)) : sum(0,6,_) : +~(_ * feedback * sier_gate(2)) * intensity * 0.88;

    bitcrush(x) = x * (1 << int(13 - intensity*10*(1-sier_gate(7)))) : int : /(1 << int(13 - intensity*10*(1-sier_gate(7)))) : ef.cubicnl(0.45*intensity, 0.3);

    chaos_lfo = (os.lf_saw(0.618 * bpm/60) & sier_gate(5)) * intensity * 2800 + 900;
    modal_filter = fi.resonlp(chaos_lfo, 6 + intensity*22, 0.85);

    // === NEW ARGENT METAL MODE 4 ===
    argent_dist = ef.cubicnl(0.9*intensity, 0.4) : fi.highpass(4, 180) : _ * (1 + 0.6*sier_gate(4));
    argent_gate = _ * (0.22 + 0.78 * sier_gate(3));
    argent_shimmer = fi.resonhp(chaos_lfo*1.6 + 1200, 8 + intensity*15, 0.7);
    argent_metal(x) = x : argent_dist : argent_gate : argent_shimmer : fractal_delay * 0.65 : _ * 1.15;

    fx = case {
        (0) => bitcrush : fi.lowpass(8, 9200);
        (1) => fractal_delay;
        (2) => _ * (0.28 + 0.72 * sier_gate(4)) : modal_filter;
        (3) => _ <: _, (* (1 + 0.85 * sier_gate(6)) : modal_filter) :> + * 0.92;
        (4) => argent_metal;  // Argent Metal — cold silver industrial distortion
    };
};