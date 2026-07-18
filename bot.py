# bot.py — البوت الرئيسي: تصفح + اشتراك + جدولة 3 مرات يومياً
# يستخدم متغير البيئة: TELEGRAM_TOKEN
# لا يحتوي على أي كود Groq أو Scraping

import os
import random
import asyncio
import datetime
import requests
import urllib.parse
import content

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── إعدادات ────────────────────────────────────────────────────────────────────
TOKEN            = os.getenv("TELEGRAM_TOKEN", "")
CHANNEL_USERNAME = "@Athar_Anthro"

# ── قنوات وبوتات الاشتراك الإجباري ──────────────────────────────────────────
REQUIRED_CHANNELS = [
    {"username": "@Athar_Anthro",     "name": "📚 قناة أثر الأنثروبولوجيا",              "url": "https://t.me/Athar_Anthro"},
    {"username": "@Athar_Dz_Islamic", "name": "🌹 قناة رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ", "url": "https://t.me/Athar_Dz_Islamic"},
]
REQUIRED_BOTS = [
    {"name": "📖 بوت علوم شرعية للأخوة والأخوات", "url": "https://t.me/Jeor_dhabh_h_a_n_i_n_bot"},
    {"name": "🕌 بوت القرآن الكريم",               "url": "https://t.me/Muhajira_for_Allah_bot"},
]

# ══════════════════════════════════════════════════════════════════════════════
# ── جلب صورة من ويكيبيديا ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _sync_fetch_wiki_image(wiki_title: str) -> str | None:
    try:
        title_encoded = urllib.parse.quote(wiki_title.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_encoded}"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "AtharAnthroBot/1.0"})
        if resp.status_code == 200:
            thumbnail = resp.json().get("thumbnail", {})
            src = thumbnail.get("source", "")
            if src:
                return src.replace("/320px-", "/800px-").replace("/200px-", "/800px-")
    except Exception as e:
        print(f"[wiki_image] {e}")
    return None

def _sync_fetch_image_bytes(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "AtharAnthroBot/1.0"})
        if resp.status_code == 200 and len(resp.content) < 9 * 1024 * 1024:
            return resp.content
    except Exception as e:
        print(f"[fetch_image] {e}")
    return None

async def fetch_wiki_image_async(wiki_title: str) -> str | None:
    return await asyncio.to_thread(_sync_fetch_wiki_image, wiki_title)

async def fetch_image_bytes_async(url: str) -> bytes | None:
    return await asyncio.to_thread(_sync_fetch_image_bytes, url)

# ══════════════════════════════════════════════════════════════════════════════
# ── أدوات مساعدة ──────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _strip_markdown(text: str) -> str:
    return text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

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
        keyboard = [
            ["📁 علم الإنسان الثقافي", "🧬 علم الإنسان الحيوي"],
            ["🏺 علم الآثار",          "🇩🇿 أنثروبولوجيا الجزائر"],
            ["🎲 معلومة عشوائية",      "💬 اقتباس علمي"],
            ["📊 حالة القناة والجدولة"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ══════════════════════════════════════════════════════════════════════════════
# ── نظام الاشتراك الإجباري ───────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def is_subscribed(bot, user_id: int, channel_username: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception as e:
        print(f"[is_subscribed] {channel_username} | {e}")
        return True  # في حالة الخطأ نفترض الاشتراك

async def check_all_subscriptions(bot, user_id: int) -> list[dict]:
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        if not await is_subscribed(bot, user_id, ch["username"]):
            not_joined.append(ch)
    return not_joined

def get_subscription_keyboard(not_joined_channels: list[dict]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(ch["name"], url=ch["url"])] for ch in not_joined_channels]
    for b in REQUIRED_BOTS:
        buttons.append([InlineKeyboardButton(b["name"], url=b["url"])])
    buttons.append([InlineKeyboardButton("✅ تحققت من اشتراكي", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def send_subscription_gate(update: Update, not_joined: list[dict]) -> None:
    names = "\n".join(f"  • {ch['name']}" for ch in not_joined)
    text = (
        "🔐 مرحباً! للوصول إلى البوت يرجى الاشتراك أولاً في:\n\n"
        f"{names}\n\n"
        "وكذلك تفعيل البوتين الشرعيين القرآنيين 👇\n\n"
        "بعد الاشتراك اضغط زر التحقق أدناه ✅"
    )
    await update.message.reply_text(text, reply_markup=get_subscription_keyboard(not_joined))

# ══════════════════════════════════════════════════════════════════════════════
# ── إرسال منشور إلى القناة ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

MORNING_HEADER = "🌅 صباح المعرفة — أنثروبولوجيا مع بداية يومك\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
NOON_HEADER    = "🔍 اكتشاف اليوم — توقف لحظة واقرأ\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
EVENING_HEADER = "🌙 قبل أن تنام — فكرة تصحبك في حُلمك\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
FOOTER         = "\n\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n📡 قناة أثر الأنثروبولوجيا | @Athar_Anthro"

def make_post_with_footer(base_post: dict, header: str) -> dict:
    return {**base_post, "text": header + base_post["text"] + FOOTER}

async def send_rich_post(bot, post: dict) -> bool:
    """يرسل منشوراً إلى القناة. يُعيد True عند النجاح."""
    text       = post["text"]
    wiki_title = post.get("wiki_title", "")
    caption    = text[:1024]

    img_bytes = None
    if wiki_title:
        try:
            image_url = await fetch_wiki_image_async(wiki_title)
            if image_url:
                img_bytes = await fetch_image_bytes_async(image_url)
        except Exception as e:
            print(f"[image_fetch] {e}")

    if img_bytes:
        try:
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_bytes, caption=caption)
            return True
        except Exception as e:
            print(f"[send_rich_post photo] {e}")

    try:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
        return True
    except Exception as e:
        print(f"[send_rich_post text] {e}")

    try:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=_strip_markdown(text))
        return True
    except Exception as e:
        print(f"[send_rich_post plain] {e}")

    return False

# ══════════════════════════════════════════════════════════════════════════════
# ── الجدولة اليومية ───────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def morning_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[morning_post] {'✅ نُشر' if ok else '❌ فشل'}")

async def noon_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    quote_obj  = random.choice(content.ANTHROPOLOGY_QUOTES)
    quote_text = (
        NOON_HEADER
        + f"💬 {quote_obj['quote']}\n\n"
        + f"✍️ {quote_obj['author']}"
        + FOOTER
    )
    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=quote_text)
        print("[noon_post] ✅ اقتباس نُشر")
    except Exception as e:
        print(f"[noon_post] ❌ {e}")

async def evening_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    seed_index = (datetime.datetime.now().day + 13) % len(content.DAILY_POSTS)
    post = make_post_with_footer(content.DAILY_POSTS[seed_index], EVENING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[evening_post] {'✅ نُشر' if ok else '❌ فشل'}")

# ══════════════════════════════════════════════════════════════════════════════
# ── أوامر المستخدم ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id   = update.effective_user.id
        not_joined = await check_all_subscriptions(context.bot, user_id)
        if not_joined:
            await send_subscription_gate(update, not_joined)
            return

        context.user_data["opened_section"] = None
        text = (
            "🌍 مرحباً بك في بوت أثر الأنثروبولوجيا!\n\n"
            "استكشف علم الإنسان العالمي والجزائري من خلال الأزرار أدناه.\n"
            "📢 القناة @Athar_Anthro تنشر تلقائياً 3 مرات يومياً مع صور!\n"
            "🤖 جديد: مقالات AI حصرية كل 30 دقيقة من Phys.org!\n\n"
            "👇 اختر من لوحة الأزرار:"
        )
        await update.message.reply_text(text, reply_markup=get_reply_keyboard())
    except Exception as e:
        print(f"[start] ❌ {e}")
        try:
            await update.message.reply_text(
                "مرحباً! اضغط على أحد الأزرار للبدء 👇",
                reply_markup=get_reply_keyboard()
            )
        except Exception as e2:
            print(f"[start fallback] ❌ {e2}")

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /post — ينشر فوراً في القناة."""
    await update.message.reply_text("⏳ جاري النشر في القناة...")
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)
    ok   = await send_rich_post(context.bot, post)
    if ok:
        await update.message.reply_text(f"✅ تم النشر في {CHANNEL_USERNAME}!")
    else:
        await update.message.reply_text("❌ فشل النشر. تحقق من صلاحيات البوت في القناة.")

async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id    = query.from_user.id
    not_joined = await check_all_subscriptions(context.bot, user_id)

    if not_joined:
        names = "\n".join(f"  • {ch['name']}" for ch in not_joined)
        await query.edit_message_text(
            f"❌ لم تشترك في جميع القنوات بعد!\n\nتبقّى:\n{names}\n\nاشترك ثم اضغط التحقق مجدداً 🔄",
            reply_markup=get_subscription_keyboard(not_joined)
        )
    else:
        await query.edit_message_text(
            "✅ أهلاً وسهلاً! تم التحقق من اشتراكك.\n\nاضغط /start للبدء 🌍"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id    = update.effective_user.id
    not_joined = await check_all_subscriptions(context.bot, user_id)
    if not_joined:
        await send_subscription_gate(update, not_joined)
        return

    text_received  = update.message.text
    current_opened = context.user_data.get("opened_section", None)

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

    collapse = {"👇 قسم الثقافي","👇 قسم الحيوي","👇 قسم الآثار","👇 قسم الجزائر","⬅️ العودة للقائمة"}
    if text_received in collapse:
        context.user_data["opened_section"] = None
        await update.message.reply_text("🔙 القائمة الرئيسية:", reply_markup=get_reply_keyboard())
        return

    content_map = {
        "📄 عرض محتوى الثقافي":           content.CULTURAL_CONTENT,
        "📄 عرض محتوى الحيوي":            content.BIOLOGICAL_CONTENT,
        "📄 عرض محتوى الآثار":            content.ARCHAEOLOGY_CONTENT,
        "📜 استكشف أنثروبولوجيا الجزائر": content.ALGERIA_CONTENT,
    }
    if text_received in content_map:
        await update.message.reply_text(
            content_map[text_received], reply_markup=get_reply_keyboard(current_opened)
        )
        return

    if text_received == "🎲 معلومة عشوائية":
        post = random.choice(content.DAILY_POSTS)
        await update.message.reply_text(post["text"], reply_markup=get_reply_keyboard(current_opened))
        return

    if text_received == "💬 اقتباس علمي":
        q   = random.choice(content.ANTHROPOLOGY_QUOTES)
        msg = f"💬 {q['quote']}\n\n✍️ {q['author']}"
        await update.message.reply_text(msg, reply_markup=get_reply_keyboard(current_opened))
        return

    if text_received == "📊 حالة القناة والجدولة":
        stats = (
            "📊 حالة النظام:\n\n"
            f"• القناة: {CHANNEL_USERNAME}\n"
            "• منشور الصباح:  🌅 09:00 جزائر (معلومة + صورة)\n"
            "• منشور الظهر:   🔍 15:00 جزائر (اقتباس علمي)\n"
            "• منشور المساء:  🌙 21:00 جزائر (معلومة + صورة)\n"
            "• 🤖 مقالات AI:  كل 30 دقيقة من Phys.org (بوت ai_bot)\n"
            "• 💬 تعليقات AI: تلقائية في المجموعة (بوت ai_bot)\n"
            f"• إجمالي المنشورات: {len(content.DAILY_POSTS)} منشوراً\n"
            f"• الاقتباسات: {len(content.ANTHROPOLOGY_QUOTES)} اقتباساً"
        )
        await update.message.reply_text(stats, reply_markup=get_reply_keyboard(current_opened))
        return

    await update.message.reply_text(
        "الرجاء الضغط على أحد الأزرار للتصفح.",
        reply_markup=get_reply_keyboard(current_opened)
    )

# ══════════════════════════════════════════════════════════════════════════════
# ── بناء تطبيق البوت (بدون تشغيل polling — يُستخدم من main.py) ───────────────
# ══════════════════════════════════════════════════════════════════════════════

def build_app() -> Application:
    """يبني ويُعيد Application جاهزاً بدون استدعاء run_polling."""
    if not TOKEN:
        raise RuntimeError("❌ TELEGRAM_TOKEN غير مضبوط")

    app = Application.builder().token(TOKEN).build()
    jq  = app.job_queue

    # الجدولة اليومية — توقيت UTC (الجزائر UTC+1)
    jq.run_daily(morning_post, time=datetime.time(hour=8,  minute=0))  # 09:00 جزائر
    jq.run_daily(noon_post,    time=datetime.time(hour=14, minute=0))  # 15:00 جزائر
    jq.run_daily(evening_post, time=datetime.time(hour=20, minute=0))  # 21:00 جزائر

    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start,    filters=private))
    app.add_handler(CommandHandler("post",  post_now, filters=private))
    app.add_handler(CallbackQueryHandler(subscription_callback, pattern="^check_sub$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & private, handle_message))

    return app


# ── تشغيل مستقل (للاختبار المباشر) ──────────────────────────────────────────
def main():
    app = build_app()
    print("🚀 bot.py يعمل — جدولة: 09:00 | 15:00 | 21:00 جزائر")
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
