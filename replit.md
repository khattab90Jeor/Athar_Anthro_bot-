# Anthropology Telegram Bot - بوت علم الإنسان

بوت تيلجرام متخصص في الأنثروبولوجيا (العالمية والجزائرية)، مبني بـ Python.

## كيفية التشغيل

### على Railway
1. اربط هذا المستودع بـ Railway.
2. أضف متغير البيئة `TELEGRAM_TOKEN` في إعدادات Railway.
3. يتعرف Railway تلقائياً على `Procfile` ويشغّل `python bot.py`.

### محلياً
```bash
pip install -r requirements.txt
TELEGRAM_TOKEN=your_token python bot.py
```

## متغيرات البيئة المطلوبة

| المتغير | الوصف |
|---------|-------|
| `TELEGRAM_TOKEN` | توكن البوت من BotFather |

## الملفات الرئيسية

- `bot.py` — الكود الرئيسي للبوت والجدولة التلقائية
- `content.py` — محتوى الأقسام والمعلومات العشوائية
- `Procfile` — أمر التشغيل على Railway
- `nixpacks.toml` — إعدادات البناء على Railway
- `requirements.txt` — المكتبات المطلوبة

## User preferences
- التشغيل الدائم يكون على Railway
