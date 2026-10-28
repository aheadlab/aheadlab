import os
import requests


def invia_telegram(testo, *, send=False, session=None):
    if not isinstance(testo, str) or not testo.strip() or len(testo) > 4096:
        raise ValueError("Messaggio richiesto (massimo 4096 caratteri)")
    if not send:
        return {"sent": False, "dry_run": True}
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise ValueError("Configurare le credenziali Telegram")
    try:
        response = (session or requests).post(f"https://api.telegram.org/bot{token}/sendMessage",
                                             json={"chat_id": chat, "text": testo}, timeout=15)
        response.raise_for_status()
        if response.json().get("ok") is not True:
            raise ValueError("Telegram rejected message")
    except Exception:
        raise RuntimeError("Invio Telegram fallito; controllare rete e configurazione") from None
    return {"sent": True, "dry_run": False}
