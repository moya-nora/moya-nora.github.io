#!/usr/bin/env python3
"""Ключ для веб-пушей Норы (VAPID). Не хранится отдельно: выводится из секрета BOT_FB_PASS,
поэтому одинаковый в каждом запуске. Если секрет поменяют, ключ сменится - тогда заново
запустить `python3 tools/vapid.py` в Actions, вписать новый публичный ключ в app-dev.html (WP_KEY)
и все подписки придётся оформить заново. Запуск без аргументов печатает только публичный ключ."""
import base64, hashlib, hmac, os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def b64(x):
    return base64.urlsafe_b64encode(x).rstrip(b"=").decode()


def keys():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        return None, None
    d = int.from_bytes(hmac.new(pw.encode(), b"nora-webpush-vapid-1", hashlib.sha256).digest(), "big") % (N - 1) + 1
    k = ec.derive_private_key(d, ec.SECP256R1())
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return b64(d.to_bytes(32, "big")), b64(pub)


if __name__ == "__main__":
    print("публичный ключ веб-пушей:", keys()[1])
