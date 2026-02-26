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

    del_time0 = 0.25;
    del_time1 = 0.333;
    del_time2 = 0.5;
    del_time3 = 0.666;
    del_time4 = 0.75;
    del_time5 = 1.0;

    feedback_path = _ * feedback * sier_gate(2);

    fractal_delay(x) = x <: 
        de.fdelay(1.8*ma.SR, del_time0*ma.SR) * sier_gate(3),
        de.fdelay(1.8*ma.SR, del_time1*ma.SR) * sier_gate(4),
        de.fdelay(1.8*ma.SR, del_time2*ma.SR) * sier_gate(5),
        de.fdelay(1.8*ma.SR, del_time3*ma.SR) * sier_gate(6),
        de.fdelay(1.8*ma.SR, del_time4*ma.SR) * sier_gate(7),
        de.fdelay(1.8*ma.SR, del_time5*ma.SR) * sier_gate(8)
        :> + : +~feedback_path : *(intensity) : *(0.88);

    bitcrush_bits = 13 - intensity*10*(1-sier_gate(7));
    bitcrush(x) = x * pow(2, bitcrush_bits) : int : /(pow(2, bitcrush_bits)) : ef.cubicnl(0.45*intensity, 0.3);

    chaos_lfo = (os.lf_saw(0.618 * bpm/60) & sier_gate(5)) * intensity * 2800 + 900;
    modal_filter = fi.resonlp(chaos_lfo, 6 + intensity*22, 0.85);

    // === NEW ARGENT METAL MODE 4 ===
    argent_dist = ef.cubicnl(0.9*intensity, 0.4) : fi.highpass(4, 180) : _ * (1 + 0.6*sier_gate(4));
    argent_gate = _ * (0.22 + 0.78 * sier_gate(3));
    argent_shimmer = fi.resonhp(chaos_lfo*1.6 + 1200, 8 + intensity*15, 0.7);
    argent_metal(x) = x : argent_dist : argent_gate : argent_shimmer : fractal_delay * 0.65 : _ * 1.15;

    effect0 = bitcrush : fi.lowpass(8, 9200);
    effect1 = fractal_delay;
    effect2 = _ * (0.28 + 0.72 * sier_gate(4)) : modal_filter;
    effect3 = _ <: _, (* (1 + 0.85 * sier_gate(6)) : modal_filter) :> + * 0.92;
    effect4 = argent_metal;

    m0 = (mode < 0.5);
    m1 = (mode > 0.5) & (mode < 1.5);
    m2 = (mode > 1.5) & (mode < 2.5);
    m3 = (mode > 2.5) & (mode < 3.5);
    m4 = (mode > 3.5);

    fx = effect0 * m0 + effect1 * m1 + effect2 * m2 + effect3 * m3 + effect4 * m4;
};