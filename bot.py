# bot.py — بوت أنثروبولوجيا قناة زوجتي 💚
# يدعم: النشر بالصور، قوالب متنوعة صباح/ظهر/مساء، اقتباسات، تصفح تفاعلي

import os
import random
import asyncio
import datetime
import requests
import urllib.parse
import content

from telegram import (
    ReplyKeyboardMarkup,
    Update,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── إعدادات البوت ─────────────────────────────────────────────────────────────
TOKEN           = os.getenv("TELEGRAM_TOKEN", "")
CHANNEL_USERNAME = "@Athar_Anthro"

# ── جلب صورة من ويكيبيديا ────────────────────────────────────────────────────
def fetch_wiki_image(wiki_title: str) -> str | None:
    """يجلب رابط صورة مصغّرة من ويكيبيديا الإنجليزية."""
    try:
        title_encoded = urllib.parse.quote(wiki_title.replace(" ", "_"))
        url = (
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_encoded}"
        )
        resp = requests.get(url, timeout=8, headers={"User-Agent": "AtharAnthroBot/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            thumbnail = data.get("thumbnail", {})
            src = thumbnail.get("source", "")
            if src:
                # نأخذ صورة بجودة أعلى قدر الإمكان
                src = src.replace("/320px-", "/800px-").replace("/200px-", "/800px-")
                return src
    except Exception as e:
        print(f"[wiki_image] خطأ: {e}")
    return None

def fetch_image_bytes(url: str) -> bytes | None:
    """يحمّل بايتات الصورة من رابطها."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "AtharAnthroBot/1.0"})
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"[fetch_image] خطأ: {e}")
    return None

# ── بناء لوحة الأزرار ─────────────────────────────────────────────────────────
def get_reply_keyboard(opened_section=None):
    if opened_section == "cultural":
        keyboard = [["📄 عرض محتوى الثقافي", "⬅️ العودة للقائمة"]]
    elif opened_section == "biological":
        keyboard = [["📄 عرض محتوى الحيوي", "⬅️ العودة للقائمة"]]
    elif opened_section == "archaeology":
        keyboard = [["📄 عرض محتوى الآثار", "⬅️ العودة للقائمة"]]
    elif opened_section == "algeria":
        keyboard = [["📜 استكشف أنثروبولوجيا الجزائر", "⬅️ العودة للقائمة"]]
    else:
        btn_cultural   = "📁 علم الإنسان الثقافي"
        btn_biological = "🧬 علم الإنسان الحيوي"
        btn_arch       = "🏺 علم الآثار"
        btn_algeria    = "🇩🇿 أنثروبولوجيا الجزائر"
        keyboard = [
            [btn_cultural, btn_biological],
            [btn_arch, btn_algeria],
            ["🎲 معلومة عشوائية", "💬 اقتباس علمي"],
            ["📊 حالة القناة والجدولة"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ── إرسال منشور ثري (نص + صورة) إلى القناة ──────────────────────────────────
def _strip_markdown(text: str) -> str:
    """يُزيل رموز Markdown للإرسال كنص عادي عند الحاجة."""
    return text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

async def send_rich_post(bot, post: dict, extra_header: str = "") -> bool:
    """
    يرسل منشوراً كاملاً (نص + صورة) إلى القناة.
    يجرب عدة طرق تدريجياً حتى ينجح أحدها.
    """
    text = extra_header + post["text"]
    wiki_title = post.get("wiki_title", "")

    # — جلب الصورة —
    img_bytes = None
    try:
        if wiki_title:
            image_url = fetch_wiki_image(wiki_title)
            if image_url:
                img_bytes = fetch_image_bytes(image_url)
                # Telegram يرفض الصور فوق 10 ميغا
                if img_bytes and len(img_bytes) > 9 * 1024 * 1024:
                    img_bytes = None
    except Exception as e:
        print(f"[image_fetch] {e}")
        img_bytes = None

    caption = text[:1024]  # حد Telegram للتعليقات على الصور

    # المحاولة 1: صورة + Markdown
    if img_bytes:
        try:
            await bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=img_bytes,
                caption=caption,
                parse_mode="Markdown",
            )
            return True
        except Exception as e:
            print(f"[try1 photo+md] {e}")

    # المحاولة 2: صورة بدون Markdown
    if img_bytes:
        try:
            await bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=img_bytes,
                caption=_strip_markdown(caption),
            )
            return True
        except Exception as e:
            print(f"[try2 photo] {e}")

    # المحاولة 3: نص فقط + Markdown
    try:
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=text,
            parse_mode="Markdown",
        )
        return True
    except Exception as e:
        print(f"[try3 text+md] {e}")

    # المحاولة 4: نص عادي بدون أي تنسيق
    try:
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=_strip_markdown(text),
        )
        return True
    except Exception as e:
        print(f"[try4 plain] {e}")

    return False

# ── قوالب المنشورات اليومية الثلاثة ─────────────────────────────────────────
MORNING_HEADER = (
    "🌅 *صباح المعرفة — أنثروبولوجيا مع بداية يومك*\n"
    "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
)

NOON_HEADER = (
    "🔍 *اكتشاف اليوم — توقف لحظة واقرأ*\n"
    "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
)

EVENING_HEADER = (
    "🌙 *قبل أن تنام — فكرة تصحبك في حُلمك*\n"
    "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
)

FOOTER = (
    "\n\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
    "📡 *قناة أثر الأنثروبولوجيا* | @Athar_Anthro"
)

def make_post_with_footer(base_post: dict, header: str) -> dict:
    """ينسخ المنشور ويضيف الترويسة والتذييل."""
    return {
        **base_post,
        "text": header + base_post["text"] + FOOTER,
    }

# ── مهام الجدولة ──────────────────────────────────────────────────────────────
async def morning_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور الصباح 9:00 — معلومة + صورة."""
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[morning_post] {'✅ نُشر' if ok else '❌ فشل'}")

async def noon_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور الظهر 15:00 — اقتباس علمي."""
    quote_obj = random.choice(content.ANTHROPOLOGY_QUOTES)
    quote_text = (
        NOON_HEADER
        + f"💬 *{quote_obj['quote']}*\n\n"
        + f"✍️ _{quote_obj['author']}_"
        + FOOTER
    )
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=quote_text,
            parse_mode="Markdown",
        )
        print("[noon_post] ✅ اقتباس نُشر")
    except Exception as e:
        print(f"[noon_post] ❌ {e}")

async def evening_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور المساء 21:00 — معلومة + صورة (مختلفة عن الصباح)."""
    # نختار منشوراً مختلفاً باستخدام الوقت كبذرة
    seed_index = (datetime.datetime.now().day + 13) % len(content.DAILY_POSTS)
    post = content.DAILY_POSTS[seed_index]
    post = make_post_with_footer(post, EVENING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[evening_post] {'✅ نُشر' if ok else '❌ فشل'}")

# ── أوامر المستخدم ────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["opened_section"] = None
    text = (
        "🌍 *مرحباً بك في بوت أثر الأنثروبولوجيا!*\n\n"
        "استكشف علم الإنسان العالمي والجزائري من خلال الأزرار أدناه.\n"
        "📢 *القناة:* @Athar_Anthro تنشر تلقائياً 3 مرات يومياً مع صور!\n\n"
        "👇 اختر من لوحة الأزرار:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_reply_keyboard())

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /post — ينشر فوراً في القناة بصورة."""
    await update.message.reply_text("⏳ جاري النشر في القناة...")
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)
    ok = await send_rich_post(context.bot, post)
    if ok:
        await update.message.reply_text(f"✅ تم النشر بنجاح في {CHANNEL_USERNAME}!")
    else:
        await update.message.reply_text(
            f"❌ فشل النشر. تأكد أن البوت مضاف كمشرف في {CHANNEL_USERNAME} بصلاحية نشر المنشورات."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_received = update.message.text
    current_opened = context.user_data.get("opened_section", None)

    # ── فتح الأقسام ──
    section_map = {
        "📁 علم الإنسان الثقافي":   ("cultural",    "📂 تم فتح القسم الثقافي:"),
        "🧬 علم الإنسان الحيوي":    ("biological",  "📂 تم فتح القسم الحيوي:"),
        "🏺 علم الآثار":            ("archaeology", "📂 تم فتح قسم الآثار:"),
        "🇩🇿 أنثروبولوجيا الجزائر": ("algeria",     "📂 تم فتح قسم الجزائر:"),
    }
    if text_received in section_map:
        section, msg = section_map[text_received]
        context.user_data["opened_section"] = section
        await update.message.reply_text(msg, reply_markup=get_reply_keyboard(section))
        return

    # ── طي / رجوع ──
    collapse = {"👇 قسم الثقافي","👇 قسم الحيوي","👇 قسم الآثار","👇 قسم الجزائر","⬅️ العودة للقائمة"}
    if text_received in collapse:
        context.user_data["opened_section"] = None
        await update.message.reply_text("🔙 القائمة الرئيسية:", reply_markup=get_reply_keyboard())
        return

    # ── عرض محتوى الأقسام ──
    content_map = {
        "📄 عرض محتوى الثقافي":           content.CULTURAL_CONTENT,
        "📄 عرض محتوى الحيوي":            content.BIOLOGICAL_CONTENT,
        "📄 عرض محتوى الآثار":            content.ARCHAEOLOGY_CONTENT,
        "📜 استكشف أنثروبولوجيا الجزائر": content.ALGERIA_CONTENT,
    }
    if text_received in content_map:
        await update.message.reply_text(
            content_map[text_received],
            parse_mode="Markdown",
            reply_markup=get_reply_keyboard(current_opened),
        )
        return

    # ── معلومة عشوائية ──
    if text_received == "🎲 معلومة عشوائية":
        post = random.choice(content.DAILY_POSTS)
        await update.message.reply_text(
            post["text"], parse_mode="Markdown", reply_markup=get_reply_keyboard(current_opened)
        )
        return

    # ── اقتباس علمي ──
    if text_received == "💬 اقتباس علمي":
        q = random.choice(content.ANTHROPOLOGY_QUOTES)
        msg = f"💬 *{q['quote']}*\n\n✍️ _{q['author']}_"
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=get_reply_keyboard(current_opened)
        )
        return

    # ── حالة القناة ──
    if text_received == "📊 حالة القناة والجدولة":
        stats = (
            f"📊 *حالة النظام:*\n\n"
            f"• القناة: {CHANNEL_USERNAME}\n"
            f"• منشور الصباح:  🌅 09:00 (معلومة + صورة)\n"
            f"• منشور الظهر:   🔍 15:00 (اقتباس علمي)\n"
            f"• منشور المساء:  🌙 21:00 (معلومة + صورة)\n"
            f"• إجمالي المنشورات المتاحة: {len(content.DAILY_POSTS)} منشوراً\n"
            f"• الاقتباسات المتاحة: {len(content.ANTHROPOLOGY_QUOTES)} اقتباساً"
        )
        await update.message.reply_text(
            stats, parse_mode="Markdown", reply_markup=get_reply_keyboard(current_opened)
        )
        return

    # ── رد افتراضي ──
    await update.message.reply_text(
        "الرجاء الضغط على أحد الأزرار للتصفح.",
        reply_markup=get_reply_keyboard(current_opened),
    )

# ── تشغيل البوت ──────────────────────────────────────────────────────────────
def main():
    if not TOKEN:
        print("❌ خطأ: يرجى إعداد متغير البيئة TELEGRAM_TOKEN")
        return

    app = Application.builder().token(TOKEN).build()
    jq  = app.job_queue

    # جدولة النشر اليومي (توقيت UTC — اضبط حسب توقيتك إن احتجت)
    jq.run_daily(morning_post, time=datetime.time(hour=6,  minute=0))   # 9:00 جزائر = 8:00 UTC في الصيف
    jq.run_daily(noon_post,    time=datetime.time(hour=12, minute=0))   # 15:00 جزائر
    jq.run_daily(evening_post, time=datetime.time(hour=19, minute=0))   # 21:00 جزائر

    # تسجيل الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post",  post_now))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت يعمل — قناة زوجتي @Athar_Anthro جاهزة للنشر 💚")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
