"""Bir video için kurgu.json'u okuyup 1080x1920 Reels MP4'ü üretir.

Kullanım: python3 araclar/reels_kurgu.py videolar/<klasör>/kurgu.json
Kurgu: sunucu görseli (yavaş yakınlaşma + her bölümde kadraj sıçraması), kartlar,
gömülü altyazı, köşe logosu, sentez ses efektleri ve (varsa) seslendirme.
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT_DIR = "/usr/share/fonts/opentype/inter/"
BLACK = FONT_DIR + "Inter-Black.otf"
XBOLD = FONT_DIR + "Inter-ExtraBold.otf"
BOLD = FONT_DIR + "Inter-Bold.otf"
EMOJI = Path("brand/grafik/emoji")
SFX = Path("brand/ses/efektler")
LOGO = "brand/logos/filigran-arma-110px.png"

RENK = {"beyaz": (255, 255, 255), "sari": (247, 183, 0)}
KIRMIZI = (203, 20, 26)
YESIL = (46, 158, 79)
KOYU = (17, 17, 17)

# Yazı bandı: sağdaki düğmelerin soluna ortalanır (bkz. brand/marka-kiti.md)
BANT_X0, BANT_X1 = 40, W - 150
KART_Y = 430
PIVOT = (540, 1150)  # yakınlaşma merkezi (sunucunun yüzü)
SUNUCU_KAYMA = 350  # sunucuyu aşağı kaydır: yüz yazı bandının altında kalsın


def font(path, size):
    return ImageFont.truetype(path, size)


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(max(x, 0.0), 1.0)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def emoji(name, size):
    return Image.open(EMOJI / f"{name}.png").convert("RGBA").resize((size, size), Image.LANCZOS)


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit(draw, text, path, start, width, max_lines=2, min_size=40):
    size = start
    while size > min_size:
        f = font(path, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= width for l in lines):
            return f, lines
        size -= 2
    f = font(path, min_size)
    return f, wrap(draw, text, f, width)


# ---------- katmanlar ----------

def arka_plan(src):
    """Sunucu görüntüsünü (fotoğraf ya da konuşan videonun bir karesi) 1080x1920 sahneye yerleştirir."""
    s = W / src.width
    src = src.resize((W, round(src.height * s)), Image.LANCZOS)
    y_off = H - src.height + SUNUCU_KAYMA
    # üst boşluğu fotoğrafın en üst satırını dikey uzatarak doldur (her sütun kendi renginde, ek yeri görünmez)
    canvas = Image.new("RGB", (W, H))
    if y_off > 0:
        strip = src.crop((0, 0, W, 6)).resize((W // 40, 1), Image.LANCZOS)
        canvas.paste(strip.resize((W, y_off), Image.BILINEAR), (0, 0))
    canvas.paste(src, (0, y_off))
    return canvas


def kamera(bg, scale, aci=0.0, dx=0.0, dy=0.0):
    """Yakınlaşma + hafif dönme/kayma (tek afin dönüşüm). scale >= 1.02 iken kenar boşluğu görünmez."""
    px, py = PIVOT
    r = math.radians(aci)
    a, b = math.cos(r) / scale, math.sin(r) / scale
    d, e = -math.sin(r) / scale, math.cos(r) / scale
    c = px - dx - (a * px + b * py)
    f = py - dy - (d * px + e * py)
    return bg.transform((W, H), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BILINEAR)


def nefes(t, sure):
    """Canlılık hareketi: yavaş baş salınımı ve nefes. Başta ve sonda sıfır (döngü bozulmasın)."""
    zarf = math.sin(math.pi * min(max(t / sure, 0), 1))
    aci = 0.7 * math.sin(2 * math.pi * t / 4.3) * zarf
    dx = 5 * math.sin(2 * math.pi * t / 5.1) * zarf
    dy = 7 * math.sin(2 * math.pi * t / 3.4) * zarf
    return aci, dx, dy


class SunucuKareleri:
    """Konuşan video varsa karelerini sırayla okur; yoksa / bitince sabit fotoğrafı verir."""

    def __init__(self, cfg):
        self.foto = Image.open(cfg["sunucu_gorsel"]).convert("RGB")
        self.sabit = arka_plan(self.foto)
        self.proc = None
        v = cfg.get("sunucu_video")
        if v:
            self.w, self.h = self.foto.size
            self.proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-i", v, "-vf", f"fps={FPS},scale={self.w}:{self.h}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def sonraki(self):
        if self.proc:
            buf = self.proc.stdout.read(self.w * self.h * 3)
            if len(buf) == self.w * self.h * 3:
                return arka_plan(Image.frombuffer("RGB", (self.w, self.h), buf))
            self.proc = None
        return self.sabit


def altyazi_satiri(parts, size=104, stroke=10):
    f = font(BLACK, size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(sum(d.textlength(t, font=f) for t, _ in parts)) + stroke * 2
    img = Image.new("RGBA", (tw + 4, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = stroke
    for t, renk in parts:
        d.text((x, 6), t, font=f, fill=RENK[renk], stroke_width=stroke, stroke_fill="black")
        x += d.textlength(t, font=f)
    return img


def etiket(text):
    f = font(BOLD, 44)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(d.textlength(text, font=f))
    img = Image.new("RGBA", (tw + 48, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, tw + 47, 71], radius=36, fill=(20, 20, 20, 235))
    d.text((24, 10), text, font=f, fill="white")
    return img


def kart(b):
    """Yanlış (kırmızı) ya da doğru (yeşil) çeviri kartı; RGBA görüntü + damga konumu döner."""
    kw = BANT_X1 - BANT_X0 - 20
    pad = 40
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if b["tip"] == "yanlis":
        ew = 190
        f, lines = fit(tmp, b["metin"], XBOLD, 70, kw - pad * 2 - ew - 30)
        lh = int(f.size * 1.18)
        body_h = max(ew, lh * len(lines))
        renk = KIRMIZI
    else:
        on_f = font(BOLD, 44)
        f, lines = fit(tmp, b["metin"], BLACK, 92, kw - pad * 2)
        lh = int(f.size * 1.15)
        body_h = 60 + lh * len(lines)
        renk = YESIL
    kh = body_h + pad * 2 + 30
    img = Image.new("RGBA", (kw + 60, kh + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = 0, 40  # kartın görüntü içindeki konumu (üstte etiket/damga payı)
    d.rounded_rectangle([ox, oy, ox + kw, oy + kh], radius=40, fill=(255, 255, 255, 248), outline=renk, width=10)
    ty = oy + pad + 30
    if b["tip"] == "yanlis":
        e = emoji(b["emoji"], ew)
        if b.get("emoji2"):
            e2 = emoji(b["emoji2"], 150)
            img.alpha_composite(e2, (ox + pad - 10, ty + 30))
            img.alpha_composite(emoji(b["emoji"], 120), (ox + pad + 90, ty - 10))
        else:
            img.alpha_composite(e, (ox + pad, ty))
        tx = ox + pad + ew + 30
        y = ty + (body_h - lh * len(lines)) // 2
        for l in lines:
            d.text((tx, y), l, font=f, fill=KIRMIZI)
            y += lh
    else:
        d.text((ox + pad, ty), b["on"], font=on_f, fill=(95, 95, 95))
        y = ty + 60
        for l in lines:
            d.text((ox + pad, y), l, font=f, fill=KOYU)
            y += lh
    lab = etiket("“" + b["deyim"] + "”")
    img.alpha_composite(lab, (ox + 28, 4))
    damga = (ox + kw - 100, 0)
    return img, damga


def kur_katmanlar(cfg):
    out = []
    for b in cfg["bolumler"]:
        k = {"b": b}
        if b["tip"] in ("kanca", "kapanis"):
            k["satirlar"] = [altyazi_satiri(p) for p in b["satirlar"]]
            if b.get("alt"):
                k["alt"] = altyazi_satiri([(b["alt"], "sari")], size=64, stroke=8)
            k["emoji"] = emoji(b["emoji"], 120)
        else:
            k["kart"], k["damga"] = kart(b)
            k["isaret"] = emoji("carpi" if b["tip"] == "yanlis" else "tik", 140)
        out.append(k)
    return out


def yapistir_olcekli(frame, img, cx, cy, scale):
    if scale <= 0.02:
        return
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def kare(cfg, bg, katmanlar, logo, t):  # bg: bu karenin sahnesi
    bols = cfg["bolumler"]
    i = next((j for j, b in enumerate(bols) if b["bas"] <= t < b["son"]), len(bols) - 1)
    b, k = bols[i], katmanlar[i]
    lt, dur = t - b["bas"], b["son"] - b["bas"]

    # arka plan: çift bölümler geniş, tek bölümler yakın kadraj; bölüm içinde yavaş yakınlaşma
    scale = (1.03 if i % 2 == 0 else 1.10) + 0.035 * (lt / dur)
    if i == len(bols) - 1:  # döngü: son 0,4 sn'de ilk kareye dön
        r = min(max((lt - (dur - 0.4)) / 0.4, 0), 1)
        scale = scale * (1 - r) + 1.03 * r
    fr = kamera(bg, scale, *nefes(t, cfg["sure"])).convert("RGBA")

    mid = (BANT_X0 + BANT_X1) / 2
    if b["tip"] in ("kanca", "kapanis"):
        y = 390
        for n, s in enumerate(k["satirlar"]):
            # ilk bölüm ilk karede tam görünür (kanca 0. saniyede okunmalı; döngü de bu kareye döner)
            sc = 1.0 if i == 0 else ease_out_back((lt - n * 0.1) / 0.2)
            cx = mid - (k["emoji"].width / 2 + 10 if n == len(k["satirlar"]) - 1 else 0)
            yapistir_olcekli(fr, s, cx, y + s.height / 2, sc)
            if n == len(k["satirlar"]) - 1:  # emoji son satırın sağında zıplar
                bounce = abs(math.sin(2 * math.pi * 1.6 * lt)) * 18
                esc = 1.0 if i == 0 else ease_out_back((lt - 0.25) / 0.2)
                yapistir_olcekli(fr, k["emoji"], cx + s.width / 2 + k["emoji"].width / 2,
                                 y + s.height / 2 - bounce, esc)
            y += 118
        if "alt" in k:
            sc = ease_out_back((lt - 0.35) / 0.2)
            yapistir_olcekli(fr, k["alt"], mid, y + 40, sc)
    else:
        kimg = k["kart"]
        sc = ease_out_back(lt / 0.18)
        cy = KART_Y + kimg.height / 2
        yapistir_olcekli(fr, kimg, mid + 10, cy, sc)
        st = 0.45 if b["tip"] == "yanlis" else 0.15
        if lt >= st:
            p = min((lt - st) / 0.12, 1)
            s2 = 1.8 - 0.8 * p
            dx, dy = k["damga"]
            x0 = mid + 10 - kimg.width / 2
            yapistir_olcekli(fr, k["isaret"], x0 + dx + 70, KART_Y + dy + 70, s2)

    fr.alpha_composite(logo, (40, 200))
    return fr.convert("RGB")


def efekt_listesi(cfg):
    ev = []
    for b in cfg["bolumler"]:
        if b["tip"] == "yanlis":
            ev += [(b["efekt"], b["bas"] + 0.05, 0.9), ("buzzer", b["bas"] + 0.45, 0.6)]
        elif b["tip"] == "dogru":
            ev.append(("ding", b["bas"] + 0.15, 0.8))
        else:
            ev.append((b["efekt"], b["bas"] + 0.02, 0.8))
    return ev


def ses_karisimi(cfg, out_wav):
    ev = efekt_listesi(cfg)
    vo = cfg.get("seslendirme")
    sfx_gain = 0.55 if vo else 1.0  # seslendirme varken efektler geri planda kalsın
    inputs, filters, labels = [], [], ""
    for n, (name, at, vol) in enumerate(ev):
        inputs += ["-i", str(SFX / f"{name}.wav")]
        ms = int(at * 1000)
        filters.append(f"[{n}:a]aresample=48000,volume={vol * sfx_gain:.3f},adelay={ms}|{ms}[e{n}]")
        labels += f"[e{n}]"
    if vo:
        inputs += ["-i", vo]
        filters.append(f"[{len(ev)}:a]aresample=48000[vo]")
        labels += "[vo]"
    total = len(ev) + (1 if vo else 0)
    filters.append(f"{labels}amix=inputs={total}:normalize=0,apad,atrim=0:{cfg['sure']},alimiter=limit=0.9[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-ac", "2", out_wav], check=True)


def main(cfg_path):
    cfg = json.loads(Path(cfg_path).read_text())
    sunucu = SunucuKareleri(cfg)
    katmanlar = kur_katmanlar(cfg)
    logo = Image.open(LOGO).convert("RGBA")
    logo.putalpha(logo.getchannel("A").point(lambda v: int(v * 0.5)))

    with tempfile.TemporaryDirectory() as td:
        vid, wav = f"{td}/v.mp4", f"{td}/a.wav"
        n = int(round(cfg["sure"] * FPS))
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
        for f in range(n):
            enc.stdin.write(kare(cfg, sunucu.sonraki(), katmanlar, logo, f / FPS).tobytes())
        enc.stdin.close()
        enc.wait()
        ses_karisimi(cfg, wav)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cfg["cikti"]],
                       check=True)
    print(cfg["cikti"])


if __name__ == "__main__":
    main(sys.argv[1])
