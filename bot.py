import os
import json
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

STATE_FILE = "state.json"

GOLD_URL = "https://api.goldprice.dev/v1/prices"
USDTRY_URL = "https://api.frankfurter.dev/v2/rate/usd/try"


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "last_news": [],
            "last_gold": None,
            "last_usdtry": None,
            "last_update_id": None
        }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def telegram_send(chat_id, message):
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True
            },
            timeout=20
        )

        if not response.ok:
            print("Telegram hatası:", response.text)

    except Exception as e:
        print("Telegram gönderim hatası:", e)


def get_updates(offset=None):
    try:
        params = {}

        if offset is not None:
            params["offset"] = offset

        response = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params=params,
            timeout=20
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print("Telegram update hatası:", e)
        return {}


def get_gold_price():
    try:
        response = requests.get(
            GOLD_URL,
            params={"symbol": "XAU-USD-SPOT"},
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        price = float(data["symbols"][0]["price"])

        return price

    except Exception as e:
        print("Altın verisi hatası:", e)
        return None


def get_usdtry():
    try:
        response = requests.get(
            USDTRY_URL,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        rate = float(data["rate"])

        return rate

    except Exception as e:
        print("USD/TRY verisi hatası:", e)
        return None


def calculate_gram_gold(gold_usd, usdtry):

    if gold_usd is None or usdtry is None:
        return None

    return gold_usd * usdtry / 31.1034768


def send_market_status(chat_id):

    gold_usd = get_gold_price()
    usdtry = get_usdtry()

    gram_gold = calculate_gram_gold(
        gold_usd,
        usdtry
    )

    if gold_usd is None or usdtry is None:

        telegram_send(
            chat_id,
            "⚠️ Piyasa verisi şu anda alınamadı.\n\n"
            "Lütfen birkaç dakika sonra tekrar deneyin."
        )

        return

    message = (
        "📊 GÜNCEL ALTIN DURUMU\n\n"
        f"🥇 XAU/USD: {gold_usd:.2f} USD\n"
        f"💵 USD/TRY: {usdtry:.4f}\n"
        f"🪙 Tahmini gram altın: {gram_gold:.2f} TL\n\n"
        "ℹ️ Gram altın değeri, "
        "ons altın × USD/TRY / 31.1034768 "
        "formülüyle yaklaşık olarak hesaplanmıştır.\n\n"
        "⚠️ Bu değer kuyumcu alış/satış fiyatı değildir."
    )

    telegram_send(
        chat_id,
        message
    )


def process_commands(state):

    last_update_id = state.get("last_update_id")

    offset = None

    if last_update_id is not None:
        offset = last_update_id + 1

    updates = get_updates(offset)

    if not updates.get("ok"):
        return

    for update in updates.get("result", []):

        update_id = update.get("update_id")

        message = update.get("message")

        if not message:
            state["last_update_id"] = update_id
            continue

        chat_id = message["chat"]["id"]

        text = message.get("text", "").strip()

        if text == "/start":

            telegram_send(
                chat_id,
                "🟡 AltınRadar32 aktif.\n\n"
                "Ben altın piyasasını takip eden karar destek botuyum.\n\n"
                "Komutlar:\n"
                "/durum - Güncel altın durumu\n"
                "/test - Telegram bağlantı testi\n"
                "/id - Chat ID bilgisi\n\n"
                "📡 Piyasa takibi aktif."
            )

        elif text == "/test":

            telegram_send(
                chat_id,
                "✅ AltınRadar32 Telegram bağlantısı çalışıyor."
            )

        elif text == "/id":

            telegram_send(
                chat_id,
                f"🆔 Chat ID: {chat_id}"
            )

        elif text == "/durum":

            send_market_status(chat_id)

        state["last_update_id"] = update_id

    save_state(state)


def main():

    print("🟡 AltınRadar32 başlatılıyor...")

    state = load_state()

    process_commands(state)

    gold_usd = get_gold_price()
    usdtry = get_usdtry()

    gram_gold = calculate_gram_gold(
        gold_usd,
        usdtry
    )

    print("XAU/USD:", gold_usd)
    print("USD/TRY:", usdtry)
    print("Gram altın:", gram_gold)

    save_state(state)

    print("✅ AltınRadar32 işlemi tamamlandı.")


if __name__ == "__main__":
    main()
