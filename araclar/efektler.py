"""Videolarda kullanılan ses efektlerini sıfırdan sentezler (lisans sorunu yok).

Kullanım: python3 araclar/efektler.py  -> brand/ses/efektler/*.wav
"""
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path("brand/ses/efektler")


def env(n, attack=0.005, decay=0.3):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t / decay)


def save(name, x, gain=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    pcm = (x * 32767).astype(np.int16)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def tone(freqs, dur, decay, attack=0.004):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in freqs)
    return x * env(n, attack, decay)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)

    # ding: doğru cevap
    save("ding", tone([(1318.5, 1.0), (2637, 0.35), (1975.5, 0.2)], 0.9, 0.25), 0.55)

    # buzzer: yanlış cevap (iki kısa kare dalga)
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.6 + np.sign(np.sin(2 * np.pi * 147 * t)) * 0.4
    b = sq * env(n, 0.003, 0.5)
    gap = np.zeros(int(SR * 0.05))
    save("buzzer", np.concatenate([b, gap, b]), 0.35)

    # pop: kart/yazı girişi
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 200
    save("pop", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.03), 0.5)

    # yutkunma: aşağı kayan "gulp"
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    f = 420 * np.exp(-t * 7) + 90
    g = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.01, 0.12)
    save("yutkunma", g, 0.6)

    # ısırma: kısa çıtırtı (filtrelenmiş gürültü patlamaları)
    parts = []
    for k in range(3):
        m = int(SR * 0.04)
        burst = rng.standard_normal(m) * env(m, 0.001, 0.01)
        burst = np.convolve(burst, np.ones(6) / 6, mode="same")
        parts += [burst, np.zeros(int(SR * 0.03))]
    save("isirma", np.concatenate(parts), 0.6)

    # zil: inharmonik çan
    save("zil", tone([(880, 1.0), (880 * 2.76, 0.5), (880 * 5.4, 0.25), (880 * 1.5, 0.3)], 1.2, 0.35, 0.002), 0.5)

    # whoosh: geçiş
    n = int(SR * 0.35)
    noise = rng.standard_normal(n)
    k = np.hanning(n)
    w = np.convolve(noise, np.ones(30) / 30, mode="same") * k
    save("whoosh", w, 0.35)


if __name__ == "__main__":
    main()
