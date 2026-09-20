import os, json, time, asyncio, logging, hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import requests
from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

load_dotenv()
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "180"))
NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "6"))

bot = Bot(TELEGRAM_TOKEN)
dp = Dispatcher()
ai = OpenAI(api_key=OPENAI_API_KEY)

last_news_ids = set()
last_alert_signature = None
last_price_snapshot = None

HEADERS = {"User-Agent": "AltinPiyasaBot/1.0"}

def yahoo_quote(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?range=1d&interval=1m"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    meta = result["meta"]
    price = meta.get("regularMarketPrice")
    prev = meta.get("previousClose")
    change = ((price - prev) / prev * 100) if price and prev else None
    return {"symbol": symbol, "price": price, "previous": prev, "change_pct": change}

def get_market():
    # XAUUSD spot proxy and USD/TRY. For production, replace with a paid
    # low-latency market-data provider if true tick-level data is required.
    gold = yahoo_quote("GC=F")       # COMEX gold futures proxy
    usdtry = yahoo_quote("USDTRY=X")
    gram = gold["price"] * usdtry["price"] / 31.1034768
    return {
        "gold_usd": gold,
        "usdtry": usdtry,
        "gram_proxy_try": gram,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def gdelt_news():
    queries = [
        "gold OR XAU OR bullion",
        "Federal Reserve OR Fed interest rates",
        "US CPI OR PCE OR inflation",
        "US jobs OR nonfarm payrolls OR unemployment",
        "Treasury yields OR dollar index OR DXY",
        "central bank gold purchases",
        "Middle East OR Ukraine OR geopolitical gold",
        "Turkey inflation OR TCMB OR USDTRY"
    ]
    out = []
    for q in queries:
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={quote(q)}&mode=artlist&maxrecords=10"
            "&format=json&sort=datedesc"
        )
        try:
            data = requests.get(url, headers=HEADERS, timeout=15).json()
            for a in data.get("articles", []):
                title = a.get("title", "").strip()
                link = a.get("url", "")
                date = a.get("seendate", "")
                if title and link:
                    uid = hashlib.sha256((title + link).encode()).hexdigest()
                    out.append({"id": uid, "title": title, "url": link, "date": date, "query": q})
        except Exception as e:
            logging.warning("GDELT error: %s", e)
    # de-duplicate
    seen, unique = set(), []
    for x in out:
        if x["id"] not in seen:
            seen.add(x["id"]); unique.append(x)
    return unique[:40]

def analyze(market, news):
    compact_news = "\n".join(
        f"- {n['title']} | {n['url']}" for n in news[:30]
    )
    prompt = f"""
Sen Türkiye'de 1.000.000 TL ile fiziksel/gram altın birikimi planlayan bir kullanıcı için
piyasa izleme ve haber analiz motorusun. Bu bir otomatik işlem sistemi değildir; al/sat
emri vermez. Güncel verileri yorumla ve belirsizliği açıkça belirt.

Piyasa:
{json.dumps(market, ensure_ascii=False, indent=2)}

Son haberler:
{compact_news}

Görevin:
1) Son haberleri önem sırasına göre grupla.
2) Her önemli haberin ons altın, USD/TRY ve dolayısıyla gram altın üzerindeki muhtemel
   yönünü "yukarı / aşağı / karışık" olarak belirt ve nedenini 1-2 cümlede açıkla.
3) Haber ile fiyat hareketi arasında doğrudan nedensellik iddiasında bulunma; yalnızca
   kaynakların desteklediği bağlantıyı kur.
4) Önümüzdeki 24-72 saat için izlenecek riskleri ve veri açıklamalarını belirt.
5) Kullanıcının 1 milyon TL'lik planı için yalnızca şu üç durumdan birini seç:
   BEKLE, KADEMELİ AL, FIRSAT ALIMI.
   Bu etiketi "yatırım tavsiyesi değil, izleme sinyali" olarak sun.
6) Fiyat eşikleri uydurma. Mevcut fiyata göre ancak açıkça "örnek izleme seviyesi"
   diye senaryo seviyeleri ver.
7) "Sert düşüş riski" için düşük/orta/yüksek şeklinde sınıflandır ve dayanaklarını yaz.

Yanıtı Türkçe, kısa ve Telegram'a uygun yaz. En başta:
🚨/🟡/🟢 başlığı + sinyal.
Sonra:
Fiyat özeti
Önemli haberler
Altına muhtemel etkisi
24-72 saat
1 milyon TL planı
Riskler
Kaynaklar
"""
    resp = ai.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5.6-mini"),
                                input=prompt)
    return resp.output_text

async def send(text):
    if CHAT_ID:
        await bot.send_message(chat_id=CHAT_ID, text=text, disable_web_page_preview=True)

@dp.message(Command("start"))
async def start(message: Message):
    global CHAT_ID
    CHAT_ID = str(message.chat.id)
    await message.answer(
        "🟡 Altın Piyasa Botu aktif.\n\n"
        "Komutlar:\n"
        "/durum — anlık piyasa + haber analizi\n"
        "/test — bildirim sistemini test et\n"
        "/id — Telegram chat ID'n\n\n"
        "Bot alım-satım emri vermez; haberleri ve piyasayı analiz ederek izleme sinyali üretir."
    )

@dp.message(Command("id"))
async def chat_id(message: Message):
    await message.answer(f"Chat ID: {message.chat.id}")

@dp.message(Command("test"))
async def test(message: Message):
    await message.answer("🔔 Test başarılı. Haber/fiyat alarm sistemi çalışıyor.")

@dp.message(Command("durum"))
async def status(message: Message):
    try:
        market = get_market()
        news = gdelt_news()
        result = analyze(market, news)
        await message.answer(result, disable_web_page_preview=True)
    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Veri alınırken hata oluştu. Logları kontrol et.")

async def monitor():
    global last_news_ids, last_alert_signature
    await asyncio.sleep(5)
    while True:
        try:
            market = get_market()
            news = gdelt_news()
            fresh = [n for n in news if n["id"] not in last_news_ids]
            last_news_ids = {n["id"] for n in news}

            # AI analysis is sent only when there is a fresh relevant-news batch.
            # This prevents unnecessary API calls every polling cycle.
            if fresh:
                result = analyze(market, fresh)
                signature = hashlib.sha256(result.encode()).hexdigest()
                if signature != last_alert_signature:
                    await send("🚨 YENİ PİYASA GELİŞMESİ\n\n" + result)
                    last_alert_signature = signature
            await asyncio.sleep(POLL_SECONDS)
        except Exception as e:
            logging.exception("monitor error: %s", e)
            await asyncio.sleep(POLL_SECONDS)

async def main():
    await asyncio.gather(dp.start_polling(bot), monitor())

if __name__ == "__main__":
    asyncio.run(main())
