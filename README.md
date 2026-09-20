# Altın Piyasa Telegram Botu

Bu proje, altını etkileyebilecek haberleri ve temel piyasa göstergelerini izleyip
Telegram üzerinden Türkçe analiz/uyarı gönderen bir başlangıç botudur.

## Neleri izliyor?

- XAU/USD için altın vadeli kontrat fiyatını proxy olarak
- USD/TRY
- Gram altın için hesaplanan yaklaşık gösterge fiyat
- Fed/faiz haberleri
- CPI/PCE/enflasyon
- ABD istihdam
- DXY/dolar ve tahvil faizleriyle ilgili haberler
- Merkez bankası altın alımları
- Jeopolitik gelişmeler
- TCMB/Türkiye enflasyon ve kur haberleri

Haberler GDELT üzerinden aranır. Fiyat verisi başlangıç sürümünde Yahoo Finance
chart endpointlerinden alınır; bu nedenle "saniyelik profesyonel veri terminali"
olarak değerlendirilmemelidir.

## 1. Telegram botunu oluştur

Telegram'da @BotFather'ı aç:
1. /newbot
2. Bot adı belirle.
3. Kullanıcı adı belirle (sonu bot ile bitmeli).
4. Verilen tokenı kopyala.

Tokenı kimseyle paylaşma.

## 2. OpenAI API anahtarı

OpenAI API anahtarını oluştur ve .env dosyasına koy.

## 3. Kurulum

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

.env içine tokenları yaz.

## 4. Çalıştır

```bash
python bot.py
```

Telegram'da botu açıp /start yaz.

Sonra:
- /durum -> hemen analiz
- /test -> bildirim testi
- /id -> chat ID

Bot, yeni haber bulunduğunda Telegram'a otomatik analiz göndermeye çalışır.

## 5. 7/24 çalıştırma

Botun gerçekten sürekli çalışması için bir VPS/cloud sunucu gerekir.
Önerilen seçenekler:
- küçük bir Linux VPS
- Docker
- systemd veya Docker restart policy

## Önemli

Bu sürüm otomatik emir göndermez ve broker hesabına erişmez.
Üretilen "BEKLE / KADEMELİ AL / FIRSAT ALIMI" ifadeleri yatırım tavsiyesi
değil, kullanıcının belirlediği 1 milyon TL'lik plan için otomatik piyasa
izleme sinyalleridir.

Üretim kullanımından önce:
- fiyat veri kaynağını düşük gecikmeli profesyonel API ile değiştirmek,
- haber kaynaklarını Reuters/Bloomberg/kurumsal ekonomik takvim gibi lisanslı
  kaynaklarla zenginleştirmek,
- duplicate haber filtresi ve güvenilirlik puanı eklemek,
- ekonomik takvim için ayrı veri sağlayıcı kullanmak,
- hata/health-check ve loglama eklemek
önerilir.
