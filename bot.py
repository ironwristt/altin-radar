import os
import time
import json
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

STATE_FILE = "state.json"

GOLD_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
    "?range=1d&interval=5m"
)

USDTRY_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X"
    "?range=1d&interval=5m"
)

NEWS_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=gold%20OR%20XAU%20OR%20Fed%20OR%20inflation%20OR%20"
    "interest%20rates%20OR%20central%20bank"
    "&mode=artlist"
    "&maxrecords=10"
    "&format=json"
    "&sort=datedesc"
)

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "last_news": [],
            "last_gold": None,
            "last_usdtry": None
        }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def telegram_send(chat_id, message):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True
            },
            timeout=20
        )
    except Exception as e:
        print("Telegram gönderim hatası:", e)


def get_updates():
    try:
        r = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            timeout=20
        )
        return r.json()
    except Exception as e:
        print("Telegram update hatası:", e)
        return {}


def get_market_price(url):
    try:
        r = requests.get(url, timeout=20)
        data = r.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]

        price = meta.get("regularMarketPrice")

        if price is None:
            quote = result["indicators"]["quote"][0]
            closes = quote["close"]
            price = closes[-1]

        return float(price)

    except Exception as e:
        print("Piyasa verisi hatası:", e)
        return None


def get_news():
    try:
        r = requests.get(NEWS_URL, timeout=30)
        data = r.json()

        return data.get("articles", [])

    except Exception as e:
        print("Haber verisi hatası:", e)
        return []


def calculate_gram_gold(gold_usd, usdtry):
    if gold_usd is None or usdtry is None:
        return None

    return gold_usd * usdtry / 31.1034768


def analyze_news(title):
    text = title.lower()

    positive_words = [
        "rate cut",
        "rate cuts",
        "interest rate cut",
        "dovish",
        "lower rates",
        "rate reduction",
        "weak jobs",
        "weak employment",
        "recession",
        "war",
        "escalation",
        "geopolitical tensions",
        "central bank buying",
        "gold purchases"
    ]

    negative_words = [
        "rate hike",
        "rate hikes",
        "hawkish",
        "higher rates",
        "strong jobs",
        "strong employment",
        "hot inflation",
        "higher inflation",
        "strong dollar",
        "dollar rises",
        "yield rises",
        "treasury yields rise"
    ]

    positive_score = sum(1 for word in positive_words if word in text)
    negative_score = sum(1 for word in negative_words if word in text)

    if positive_score > negative_score:
        return "POZİTİF", "Altın açısından yukarı yönlü destekleyici olabilir."
    elif negative_score > positive_score:
        return "NEGATİF", "Altın üzerinde aşağı yönlü baskı oluşturabilir."
    else:
        return "NÖTR", "Altın açısından belirgin bir yön sinyali vermiyor."


def create_market_message(gold_usd, usdtry, gram_gold, previous_gold):
    if gram_gold is None:
        return None

    change = None

    if previous_gold:
        change = ((gold_usd - previous_gold) / previous_gold) * 100

    if change is None:
        trend = "Veri oluşturuluyor"
    elif change > 0.5:
        trend = "Yukarı yönlü hareket"
    elif change < -0.5:
        trend = "Aşağı yönlü hareket"
    else:
        trend = "Yatay / sınırlı hareket"

    if change is not None and change < -1:
        signal = "FIRSAT ALIMI İNCELENEBİLİR"
    elif change is not None and change < -0.4:
        signal = "KADEMELİ ALIM İNCELENEBİLİR"
    elif change is not None and change > 1:
        signal = "BEKLE / ACELE ETME"
    else:
        signal = "BEKLE / VERİ TAKİBİ"

    message = (
        "🟡 ALTIN RADAR 32\n\n"
        f"📊 XAU/USD: {gold_usd:.2f} USD\n"
        f"💵 USD/TRY: {usdtry:.4f}\n"
        f"🥇 Tahmini gram altın: {gram_gold:.2f} TL\n\n"
        f"📈 Durum: {trend}\n"
    )

    if change is not None:
        message += f"📉 Değişim: %{change:.2f}\n"

    message += (
        f"\n🎯 Radar sinyali: {signal}\n\n"
        "⚠️ Bu sinyal otomatik al-sat emri değildir. "
        "Piyasa verilerine dayalı karar desteğidir.\n\n"
        "💰 1.000.000 TL yatırım planında tek seferde işlem "
        "yerine kademeli alım yaklaşımı değerlendirilebilir."
    )

    return message


def process_commands(state):
    updates = get_updates()

    if not updates.get("ok"):
        return

    for update in updates.get("result", []):

        update_id = update.get("update_id")

        message = update.get("message")

        if not message:
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
                "📡 Piyasa ve haber takibi otomatik yapılacaktır."
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

            gold_usd = get_market_price(GOLD_URL)
            usdtry = get_market_price(USDTRY_URL)

            gram_gold = calculate_gram_gold(
                gold_usd,
                usdtry
            )

            if gram_gold:
                telegram_send(
                    chat_id,
                    (
                        "📊 GÜNCEL ALTIN DURUMU\n\n"
                        f"XAU/USD: {gold_usd:.2f}\n"
                        f"USD/TRY: {usdtry:.4f}\n"
                        f"Tahmini gram altın: {gram_gold:.2f} TL\n\n"
                        "ℹ️ Gram değer, ons altın ve USD/TRY "
                        "üzerinden yaklaşık hesaplanmıştır."
                    )
                )

        state["last_update_id"] = update_id

    save_state(state)


def main():

    state = load_state()

    process_commands(state)

    gold_usd = get_market_price(GOLD_URL)
    usdtry = get_market_price(USDTRY_URL)

    gram_gold = calculate_gram_gold(
        gold_usd,
        usdtry
    )

    print("XAU/USD:", gold_usd)
    print("USD/TRY:", usdtry)
    print("Gram altın:", gram_gold)

    if gold_usd is not None and usdtry is not None:

        market_message = create_market_message(
            gold_usd,
            usdtry,
            gram_gold,
            state.get("last_gold")
        )

        # İlk çalışmada sadece veri kaydedilir.
        if state.get("last_gold") is None:
            state["last_gold"] = gold_usd
            state["last_usdtry"] = usdtry

        else:
            # Büyük hareket varsa Telegram'a gönder.
            change = (
                (gold_usd - state["last_gold"])
                / state["last_gold"]
            ) * 100

            if abs(change) >= 0.6:

                updates = get_updates()

                chat_ids = set()

                for update in updates.get("result", []):
                    msg = update.get("message")

                    if msg:
                        chat_ids.add(msg["chat"]["id"])

                for chat_id in chat_ids:
                    if market_message:
                        telegram_send(
                            chat_id,
                            market_message
                        )

            state["last_gold"] = gold_usd
            state["last_usdtry"] = usdtry

    # Haber kontrolü
    news = get_news()

    old_news = set(state.get("last_news", []))

    for article in news:

        title = article.get("title", "")

        if not title:
            continue

        url = article.get("url", "")

        news_id = title + url

        if news_id in old_news:
            continue

        impact, explanation = analyze_news(title)

        if impact == "NÖTR":
            continue

        updates = get_updates()

        chat_ids = set()

        for update in updates.get("result", []):
            msg = update.get("message")

            if msg:
                chat_ids.add(msg["chat"]["id"])

        message = (
            "🚨 ALTINRADAR32 HABER UYARISI\n\n"
            f"📰 {title}\n\n"
            f"📌 Etki: {impact}\n"
            f"📊 Değerlendirme: {explanation}\n\n"
            "💰 1.000.000 TL yatırım planı açısından "
            "bu gelişme tek başına alım/satım kararı "
            "olarak değerlendirilmemelidir.\n\n"
            f"🔗 Kaynak: {url}"
        )

        for chat_id in chat_ids:
            telegram_send(chat_id, message)

        old_news.add(news_id)

    state["last_news"] = list(old_news)[-100:]

    save_state(state)


if __name__ == "__main__":
    main()
