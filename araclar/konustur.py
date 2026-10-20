"""Sabit bir sunucu fotoğrafını verilen sese göre konuşturur (MuseTalk v1.5, CPU).

Kurulum (bir kez): /opt/musetalk altında MuseTalk kodu, venv ve ağırlıklar (bkz. araclar/README.md).
Kullanım:
  /opt/musetalk/venv/bin/python araclar/konustur.py SES.wav CIKTI.mp4 [--fps 30]

Notlar
- Yüz kutusu ve ağız maskesi brand/sunucu/zeynep-yuz.json'dan okunur (fotoğraf sabit olduğu
  için yüz noktaları bir kez ölçüldü; MuseTalk'un DWPose/yüz ayrıştırma adımları gerekmez).
- MuseTalk kodu MIT, model ağırlıkları ticari kullanıma açık (TMElyralab/MuseTalk);
  sd-vae-ft-mse (MIT), whisper-tiny (MIT).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch

MUSETALK = Path(os.environ.get("MUSETALK_DIR", "/opt/musetalk"))
sys.path.insert(0, str(MUSETALK / "code"))

from transformers import WhisperModel  # noqa: E402
from musetalk.models.unet import PositionalEncoding, UNet  # noqa: E402
from musetalk.models.vae import VAE  # noqa: E402
from musetalk.utils.audio_processor import AudioProcessor  # noqa: E402

YUZ = Path("brand/sunucu/zeynep-yuz.json")


def agiz_maskesi(h, w, yuz):
    """Ağız-çene bölgesini kapsayan yumuşak kenarlı elips maske (0-1, float32)."""
    m = np.zeros((h, w), np.float32)
    cx, cy = yuz["agiz_merkez"]
    rx, ry = yuz["maske_yaricap"]
    cv2.ellipse(m, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)
    k = yuz["maske_yumusatma"] | 1
    return cv2.GaussianBlur(m, (k, k), 0)


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ses")
    ap.add_argument("cikti")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    torch.set_num_threads(os.cpu_count())
    yuz = json.loads(YUZ.read_text())
    frame = cv2.imread(yuz["gorsel"])  # BGR
    H, W = frame.shape[:2]
    x1, y1, x2, y2 = yuz["kutu"]

    models = MUSETALK / "models"
    vae = VAE(model_path=str(models / "sd-vae"))
    unet = UNet(unet_config=str(models / "musetalkV15" / "musetalk.json"),
                model_path=str(models / "musetalkV15" / "unet.pth"), device=torch.device("cpu"))
    pe = PositionalEncoding(d_model=384)
    whisper = WhisperModel.from_pretrained(str(models / "whisper")).eval()
    audio = AudioProcessor(feature_extractor_path=str(models / "whisper"))

    feats, n_samples = audio.get_audio_feature(args.ses)
    chunks = audio.get_whisper_chunk(feats, "cpu", unet.model.dtype, whisper, n_samples, fps=args.fps,
                                     audio_padding_length_left=2, audio_padding_length_right=2)

    crop = cv2.resize(frame[y1:y2, x1:x2], (256, 256), interpolation=cv2.INTER_LANCZOS4)
    latent = vae.get_latents_for_unet(crop)
    t0 = torch.tensor([0])

    mask = agiz_maskesi(H, W, yuz)[..., None]
    base = frame.astype(np.float32)

    with tempfile.TemporaryDirectory() as td:
        n = len(chunks)
        for b in range(0, n, args.batch):
            wb = chunks[b:b + args.batch]
            lat = latent.repeat(len(wb), 1, 1, 1)
            pred = unet.model(lat, t0, encoder_hidden_states=pe(wb)).sample
            for k, face in enumerate(vae.decode_latents(pred)):
                face = cv2.resize(face, (x2 - x1, y2 - y1), interpolation=cv2.INTER_CUBIC)
                out = base.copy()
                out[y1:y2, x1:x2] = face
                out = base * (1 - mask) + out * mask
                cv2.imwrite(f"{td}/{b + k:06d}.png", out.clip(0, 255).astype(np.uint8))
            print(f"{min(b + args.batch, n)}/{n}", flush=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", f"{td}/%06d.png",
                        "-i", args.ses, "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", args.cikti], check=True)
    print(args.cikti)


if __name__ == "__main__":
    main()
