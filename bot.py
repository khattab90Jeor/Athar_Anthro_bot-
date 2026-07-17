# bot.py — بوت أنثروبولوجيا قناة زوجتي 💚
# يدعم: النشر بالصور، قوالب متنوعة صباح/ظهر/مساء، اقتباسات، تصفح تفاعلي
# + ذكاء اصطناعي: سحب مقالات Phys.org كل ساعة + تعليقات تلقائية بـ Groq

import os
import random
import asyncio
import datetime
import requests
import urllib.parse
import content

from bs4 import BeautifulSoup
from groq import Groq

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── إعدادات البوت ─────────────────────────────────────────────────────────────
TOKEN            = os.getenv("TELEGRAM_TOKEN", "")
CHANNEL_USERNAME = "@Athar_Anthro"
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")

# ── عميل Groq ─────────────────────────────────────────────────────────────────
_groq_client: Groq | None = None

def get_groq_client() -> Groq | None:
    """يُنشئ عميل Groq مرة واحدة ويُعيد استخدامه."""
    global _groq_client
    if _groq_client is None and GROQ_API_KEY:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

# ── ذاكرة منع التكرار لمقالات Phys.org ──────────────────────────────────────
_last_published_article_url: str = ""

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
# ── جلب صورة من ويكيبيديا (async-safe عبر thread) ───────────────────────────
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
                src = src.replace("/320px-", "/800px-").replace("/200px-", "/800px-")
                return src
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
# ── سحب مقالات Phys.org (BeautifulSoup) ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

PHYS_ORG_URL = "https://phys.org/anthropology-news/"
HEADERS_SCRAPER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def _sync_scrape_latest_phys_article() -> dict | None:
    """
    [sync] يسحب أحدث مقال أنثروبولوجي من Phys.org.
    يُعيد dict يحتوي: url, title, summary, image_url
    أو None عند الفشل.
    """
    try:
        resp = requests.get(PHYS_ORG_URL, timeout=15, headers=HEADERS_SCRAPER)
        if resp.status_code != 200:
            print(f"[phys_scrape] status {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # ابحث عن أول مقال في قائمة الأخبار
        article_link = None
        article_title = ""

        # هيكل Phys.org: <article> أو .news-block أو h3 > a
        for tag in soup.select("article h3 a, .sorted-article-title a, .news-title a, h3.mb-1 a"):
            href = tag.get("href", "")
            if href and "/news/" in href:
                article_link = href if href.startswith("http") else "https://phys.org" + href
                article_title = tag.get_text(strip=True)
                break

        # بديل: ابحث في جميع الروابط
        if not article_link:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/news/" in href and href.endswith(".html"):
                    full = href if href.startswith("http") else "https://phys.org" + href
                    article_link = full
                    article_title = a.get_text(strip=True)
                    break

        if not article_link:
            print("[phys_scrape] لم يُعثر على أي رابط مقال")
            return None

        # اسحب صفحة المقال
        art_resp = requests.get(article_link, timeout=15, headers=HEADERS_SCRAPER)
        if art_resp.status_code != 200:
            return None

        art_soup = BeautifulSoup(art_resp.text, "html.parser")

        # عنوان المقال
        h1 = art_soup.find("h1")
        if h1:
            article_title = h1.get_text(strip=True)

        # ملخص / أول فقرة
        summary_parts = []
        for p in art_soup.select("article p, .article-main p, .text-block p"):
            t = p.get_text(strip=True)
            if len(t) > 60:
                summary_parts.append(t)
            if len(summary_parts) >= 3:
                break
        summary = " ".join(summary_parts) if summary_parts else article_title

        # صورة المقال
        image_url = None
        for img_tag in art_soup.select("article img, .article-main img, figure img"):
            src = img_tag.get("src") or img_tag.get("data-src") or ""
            if src and src.startswith("http") and any(ext in src for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                image_url = src
                break

        return {
            "url": article_link,
            "title": article_title,
            "summary": summary[:2000],  # اقتصر النص لحد Groq المعقول
            "image_url": image_url,
        }

    except Exception as e:
        print(f"[phys_scrape] خطأ: {e}")
        return None


def _sync_groq_translate_article(title: str, summary: str) -> str | None:
    """
    [sync] يُرسل عنوان المقال وملخصه إلى Groq ليُترجمه ويُصيغه بأسلوب أنثروبولوجي عربي.
    """
    client = get_groq_client()
    if not client:
        print("[groq_translate] لا يوجد GROQ_API_KEY")
        return None

    prompt = (
        "أنت خبير في علم الإنسان (الأنثروبولوجيا) وكاتب عربي متمكن. "
        "لديك المقال العلمي التالي باللغة الإنجليزية:\n\n"
        f"العنوان: {title}\n\n"
        f"المحتوى: {summary}\n\n"
        "المطلوب: اكتب منشوراً علمياً جذاباً بالعربية الفصحى لقناة تيليغرام متخصصة في الأنثروبولوجيا. "
        "اتبع هذا الأسلوب:\n"
        "- ابدأ بعنوان مشوق يحتوي إيموجي مناسب\n"
        "- اشرح الاكتشاف أو الدراسة بأسلوب علمي شيق لا جاف\n"
        "- أضف سياقاً أنثروبولوجياً يربط الموضوع بالإنسانية الكبرى\n"
        "- اختم بجملة تُلهم التفكير أو سؤال للتأمل\n"
        "- الطول المثالي: 150 إلى 250 كلمة\n"
        "- استخدم **تمييز الأجزاء المهمة** بنجمتين للـ Markdown\n\n"
        "اكتب المنشور مباشرة دون مقدمة أو شرح إضافي."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.75,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq_translate] خطأ: {e}")
        return None


def _sync_groq_generate_comment(post_text: str) -> str | None:
    """
    [sync] يُولّد تعليقاً أنثروبولوجياً ذكياً على منشور القناة باستخدام Groq.
    """
    client = get_groq_client()
    if not client:
        return None

    prompt = (
        "أنت خبير في علم الإنسان (الأنثروبولوجيا) ومعلم شغوف. "
        "قناة تيليغرام أنثروبولوجية نشرت للتو هذا المنشور:\n\n"
        f"{post_text[:1500]}\n\n"
        "المطلوب: اكتب تعليقاً علمياً قصيراً (60 إلى 100 كلمة) يُضيف:\n"
        "- معلومة تكميلية مفيدة أو منظور أنثروبولوجي مختلف\n"
        "- مقارنة ثقافية أو مثال من حضارة أخرى إن أمكن\n"
        "- اختم بسؤال يُحفّز المتابعين على التفاعل\n"
        "- الأسلوب: دافئ وعلمي، لا رسمي بزيادة\n\n"
        "اكتب التعليق مباشرة بالعربية دون مقدمة."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq_comment] خطأ: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# ── بناء لوحة الأزرار ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════════════════════════════
# ── إرسال منشور ثري (نص + صورة) إلى القناة ──────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _strip_markdown(text: str) -> str:
    return text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

async def send_rich_post(bot, post: dict, extra_header: str = "") -> bool:
    """
    يرسل منشوراً كاملاً (نص + صورة) إلى القناة.
    يجرب عدة طرق تدريجياً حتى ينجح أحدها.
    """
    text = extra_header + post["text"]
    wiki_title = post.get("wiki_title", "")

    img_bytes = None
    try:
        if wiki_title:
            image_url = await fetch_wiki_image_async(wiki_title)
            if image_url:
                img_bytes = await fetch_image_bytes_async(image_url)
    except Exception as e:
        print(f"[image_fetch] {e}")
        img_bytes = None

    caption = text[:1024]

    if img_bytes:
        try:
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_bytes,
                                 caption=caption, parse_mode="Markdown")
            return True
        except Exception as e:
            print(f"[try1 photo+md] {e}")

    if img_bytes:
        try:
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_bytes,
                                 caption=_strip_markdown(caption))
            return True
        except Exception as e:
            print(f"[try2 photo] {e}")

    try:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="Markdown")
        return True
    except Exception as e:
        print(f"[try3 text+md] {e}")

    try:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=_strip_markdown(text))
        return True
    except Exception as e:
        print(f"[try4 plain] {e}")

    return False

# ══════════════════════════════════════════════════════════════════════════════
# ── قوالب المنشورات اليومية الثلاثة ─────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

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
    return {
        **base_post,
        "text": header + base_post["text"] + FOOTER,
    }

# ══════════════════════════════════════════════════════════════════════════════
# ── مهام الجدولة اليومية (الأصلية — لا تُعدَّل) ─────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def morning_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور الصباح 9:00 جزائر — معلومة + صورة."""
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[morning_post] {'✅ نُشر' if ok else '❌ فشل'}")

async def noon_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور الظهر 15:00 جزائر — اقتباس علمي."""
    quote_obj = random.choice(content.ANTHROPOLOGY_QUOTES)
    quote_text = (
        NOON_HEADER
        + f"💬 *{quote_obj['quote']}*\n\n"
        + f"✍️ _{quote_obj['author']}_"
        + FOOTER
    )
    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME,
                                       text=quote_text, parse_mode="Markdown")
        print("[noon_post] ✅ اقتباس نُشر")
    except Exception as e:
        print(f"[noon_post] ❌ {e}")

async def evening_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """منشور المساء 21:00 جزائر — معلومة + صورة (مختلفة عن الصباح)."""
    seed_index = (datetime.datetime.now().day + 13) % len(content.DAILY_POSTS)
    post = content.DAILY_POSTS[seed_index]
    post = make_post_with_footer(post, EVENING_HEADER)
    ok = await send_rich_post(context.bot, post)
    print(f"[evening_post] {'✅ نُشر' if ok else '❌ فشل'}")

# ══════════════════════════════════════════════════════════════════════════════
# ── جدولة الذكاء الاصطناعي — مقالات Phys.org كل ساعة ────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_and_publish_ai_article(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يعمل كل ساعة.
    يسحب أحدث مقال من Phys.org Anthropology، يُترجمه بـ Groq،
    وينشره في القناة مع صورة المقال.
    يمنع تكرار نشر نفس المقال باستخدام ذاكرة المتغير _last_published_article_url.
    """
    global _last_published_article_url

    print("[ai_scraper] 🔄 بدء سحب مقال من Phys.org ...")

    # سحب بيانات المقال في thread منفصل
    article = await asyncio.to_thread(_sync_scrape_latest_phys_article)

    if not article:
        print("[ai_scraper] ❌ لم يُعثر على مقال")
        return

    # منع التكرار
    if article["url"] == _last_published_article_url:
        print(f"[ai_scraper] ⏭️ نفس المقال السابق، تم التخطي: {article['url']}")
        return

    print(f"[ai_scraper] 📰 مقال جديد: {article['title']}")

    # ترجمة وصياغة عبر Groq
    arabic_text = await asyncio.to_thread(
        _sync_groq_translate_article, article["title"], article["summary"]
    )

    if not arabic_text:
        print("[ai_scraper] ❌ فشل Groq في الترجمة")
        return

    # بناء نص المنشور النهائي
    ai_header = (
        "🤖 *اكتشاف علمي جديد — مباشرة من المجلات العالمية*\n"
        "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
    )
    ai_footer = (
        f"\n\n🔗 [المصدر الأصلي]({article['url']})\n"
        "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
        "📡 *قناة أثر الأنثروبولوجيا* | @Athar_Anthro"
    )

    full_text = ai_header + arabic_text + ai_footer
    caption   = full_text[:1024]

    # محاولة النشر مع الصورة الحصرية للمقال
    published = False
    image_url = article.get("image_url")

    if image_url:
        img_bytes = await fetch_image_bytes_async(image_url)

        if img_bytes:
            # محاولة 1: صورة + Markdown
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_USERNAME, photo=img_bytes,
                    caption=caption, parse_mode="Markdown"
                )
                published = True
                print("[ai_scraper] ✅ نُشر بصورة المقال + Markdown")
            except Exception as e:
                print(f"[ai_scraper try1] {e}")

            # محاولة 2: صورة بدون Markdown
            if not published:
                try:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_USERNAME, photo=img_bytes,
                        caption=_strip_markdown(caption)
                    )
                    published = True
                    print("[ai_scraper] ✅ نُشر بصورة المقال (بدون تنسيق)")
                except Exception as e:
                    print(f"[ai_scraper try2] {e}")

    # محاولة 3: نص فقط + Markdown
    if not published:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME, text=full_text, parse_mode="Markdown"
            )
            published = True
            print("[ai_scraper] ✅ نُشر نصاً (Markdown)")
        except Exception as e:
            print(f"[ai_scraper try3] {e}")

    # محاولة 4: نص عادي
    if not published:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME, text=_strip_markdown(full_text)
            )
            published = True
            print("[ai_scraper] ✅ نُشر نصاً عادياً")
        except Exception as e:
            print(f"[ai_scraper try4] {e}")

    if published:
        _last_published_article_url = article["url"]
    else:
        print("[ai_scraper] ❌ فشل النشر بعد 4 محاولات")

# ══════════════════════════════════════════════════════════════════════════════
# ── نظام التعليقات التلقائي (CHANNEL_POST → Groq → تعليق في المجموعة) ────────
# ══════════════════════════════════════════════════════════════════════════════

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يستمع لكل منشور جديد في القناة وينشر تعليقاً ذكياً بـ Groq
    في مجموعة النقاش المرتبطة بالقناة.
    """
    channel_post = update.channel_post
    if not channel_post:
        return

    # تأكد أن المنشور من قناتنا فقط
    chat_username = (channel_post.chat.username or "").lower()
    if chat_username not in ("athar_anthro", "@athar_anthro"):
        return

    # استخرج نص المنشور
    post_text = channel_post.text or channel_post.caption or ""
    if not post_text.strip():
        return

    print(f"[channel_post_handler] 📩 منشور جديد id={channel_post.message_id}")

    # ابحث عن مجموعة النقاش المرتبطة بالقناة
    discussion_group_id: int | None = None
    try:
        channel_chat = await context.bot.get_chat(CHANNEL_USERNAME)
        discussion_group_id = getattr(channel_chat, "linked_chat_id", None)
    except Exception as e:
        print(f"[channel_post_handler] تعذّر الحصول على linked_chat_id: {e}")

    if not discussion_group_id:
        print("[channel_post_handler] لا توجد مجموعة نقاش مرتبطة أو لم يُحدَّد المعرّف")
        return

    # توليد التعليق عبر Groq في thread منفصل
    comment_text = await asyncio.to_thread(_sync_groq_generate_comment, post_text)

    if not comment_text:
        print("[channel_post_handler] ❌ Groq لم يُولّد تعليقاً")
        return

    # إرسال التعليق في مجموعة النقاش كردّ على المنشور
    try:
        await context.bot.send_message(
            chat_id=discussion_group_id,
            text=comment_text,
            reply_to_message_id=channel_post.message_id,
            parse_mode="Markdown",
        )
        print("[channel_post_handler] ✅ تعليق Groq نُشر في مجموعة النقاش")
    except Exception as e:
        # جرب بدون Markdown
        try:
            await context.bot.send_message(
                chat_id=discussion_group_id,
                text=_strip_markdown(comment_text),
                reply_to_message_id=channel_post.message_id,
            )
            print("[channel_post_handler] ✅ تعليق Groq نُشر (بدون Markdown)")
        except Exception as e2:
            print(f"[channel_post_handler] ❌ فشل إرسال التعليق: {e2}")

# ══════════════════════════════════════════════════════════════════════════════
# ── نظام الاشتراك الإجباري ───────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def is_subscribed(bot, user_id: int, channel_username: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        status = member.status
        print(f"[is_subscribed] {channel_username} | user={user_id} | status={status}")
        return status not in ("left", "kicked", "banned")
    except Exception as e:
        print(f"[is_subscribed] {channel_username} | خطأ: {e}")
        return True

async def check_all_subscriptions(bot, user_id: int) -> list[dict]:
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        if not await is_subscribed(bot, user_id, ch["username"]):
            not_joined.append(ch)
    return not_joined

def get_subscription_keyboard(not_joined_channels: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for ch in not_joined_channels:
        buttons.append([InlineKeyboardButton(ch["name"], url=ch["url"])])
    for bot_info in REQUIRED_BOTS:
        buttons.append([InlineKeyboardButton(bot_info["name"], url=bot_info["url"])])
    buttons.append([InlineKeyboardButton("✅ تحققت من اشتراكي", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

def get_all_channels_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for ch in REQUIRED_CHANNELS:
        buttons.append([InlineKeyboardButton(ch["name"], url=ch["url"])])
    for bot_info in REQUIRED_BOTS:
        buttons.append([InlineKeyboardButton(bot_info["name"], url=bot_info["url"])])
    buttons.append([InlineKeyboardButton("✅ تحققت من اشتراكي", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def send_subscription_gate(update: Update, not_joined: list[dict]) -> None:
    names = "\n".join(f"  • {ch['name']}" for ch in not_joined)
    text = (
        "🔐 *مرحباً! للوصول إلى البوت يرجى الاشتراك أولاً في:*\n\n"
        f"{names}\n\n"
        "وكذلك تفعيل البوتين الشرعيين القرآنيين 👇\n\n"
        "_بعد الاشتراك اضغط زر التحقق أدناه_ ✅"
    )
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=get_subscription_keyboard(not_joined))

async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    not_joined = await check_all_subscriptions(context.bot, user_id)

    if not_joined:
        names = "\n".join(f"  • {ch['name']}" for ch in not_joined)
        text = (
            "❌ *لم تشترك في جميع القنوات بعد!*\n\n"
            f"تبقّى عليك الاشتراك في:\n{names}\n\n"
            "_اشترك ثم اضغط التحقق مجدداً_ 🔄"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=get_subscription_keyboard(not_joined))
    else:
        await query.edit_message_text(
            "✅ *أهلاً وسهلاً! تم التحقق من اشتراكك.*\n\n"
            "اضغط /start للبدء 🌍",
            parse_mode="Markdown",
        )

# ══════════════════════════════════════════════════════════════════════════════
# ── أوامر المستخدم ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    not_joined = await check_all_subscriptions(context.bot, user_id)
    if not_joined:
        await send_subscription_gate(update, not_joined)
        return

    context.user_data["opened_section"] = None
    text = (
        "🌍 *مرحباً بك في بوت أثر الأنثروبولوجيا!*\n\n"
        "استكشف علم الإنسان العالمي والجزائري من خلال الأزرار أدناه.\n"
        "📢 *القناة:* @Athar_Anthro تنشر تلقائياً 3 مرات يومياً مع صور!\n"
        "🤖 *جديد:* مقالات علمية حصرية كل ساعة من أحدث الأبحاث العالمية!\n\n"
        "👇 اختر من لوحة الأزرار:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_reply_keyboard())

async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /post — ينشر فوراً في القناة بصورة."""
    await update.message.reply_text("⏳ جاري النشر في القناة...")
    post = make_post_with_footer(random.choice(content.DAILY_POSTS), MORNING_HEADER)

    last_error = None
    text       = post["text"]
    wiki_title = post.get("wiki_title", "")
    caption    = text[:1024]

    img_bytes = None
    try:
        if wiki_title:
            image_url = await fetch_wiki_image_async(wiki_title)
            if image_url:
                img_bytes = await fetch_image_bytes_async(image_url)
    except Exception as e:
        last_error = f"جلب الصورة: {e}"
        print(f"[post_now image] {e}")

    if img_bytes:
        try:
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_bytes,
                                         caption=caption, parse_mode="Markdown")
            await update.message.reply_text(f"✅ تم النشر بصورة في {CHANNEL_USERNAME}!")
            return
        except Exception as e:
            last_error = f"صورة+md: {e}"

    if img_bytes:
        try:
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_bytes,
                                         caption=_strip_markdown(caption))
            await update.message.reply_text(f"✅ تم النشر بصورة (بدون تنسيق) في {CHANNEL_USERNAME}!")
            return
        except Exception as e:
            last_error = f"صورة: {e}"

    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=text, parse_mode="Markdown")
        await update.message.reply_text(f"✅ تم النشر (نص) في {CHANNEL_USERNAME}!")
        return
    except Exception as e:
        last_error = f"نص+md: {e}"

    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=_strip_markdown(text))
        await update.message.reply_text(f"✅ تم النشر (نص عادي) في {CHANNEL_USERNAME}!")
        return
    except Exception as e:
        last_error = f"نص عادي: {e}"

    await update.message.reply_text(
        f"❌ فشل النشر بعد 4 محاولات.\nآخر خطأ: `{last_error}`",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    not_joined = await check_all_subscriptions(context.bot, user_id)
    if not_joined:
        await send_subscription_gate(update, not_joined)
        return

    text_received  = update.message.text
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

    # ── رجوع ──
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
        await update.message.reply_text(content_map[text_received], parse_mode="Markdown",
                                        reply_markup=get_reply_keyboard(current_opened))
        return

    # ── معلومة عشوائية ──
    if text_received == "🎲 معلومة عشوائية":
        post = random.choice(content.DAILY_POSTS)
        await update.message.reply_text(post["text"], parse_mode="Markdown",
                                        reply_markup=get_reply_keyboard(current_opened))
        return

    # ── اقتباس علمي ──
    if text_received == "💬 اقتباس علمي":
        q = random.choice(content.ANTHROPOLOGY_QUOTES)
        msg = f"💬 *{q['quote']}*\n\n✍️ _{q['author']}_"
        await update.message.reply_text(msg, parse_mode="Markdown",
                                        reply_markup=get_reply_keyboard(current_opened))
        return

    # ── حالة القناة ──
    if text_received == "📊 حالة القناة والجدولة":
        groq_status = "✅ مفعّل" if GROQ_API_KEY else "❌ غير مفعّل (أضف GROQ_API_KEY)"
        stats = (
            f"📊 *حالة النظام:*\n\n"
            f"• القناة: {CHANNEL_USERNAME}\n"
            f"• منشور الصباح:  🌅 09:00 (معلومة + صورة)\n"
            f"• منشور الظهر:   🔍 15:00 (اقتباس علمي)\n"
            f"• منشور المساء:  🌙 21:00 (معلومة + صورة)\n"
            f"• 🤖 مقالات AI:  كل ساعة من Phys.org\n"
            f"• 💬 تعليقات AI: تلقائية على كل منشور\n"
            f"• Groq API: {groq_status}\n"
            f"• إجمالي المنشورات المتاحة: {len(content.DAILY_POSTS)} منشوراً\n"
            f"• الاقتباسات المتاحة: {len(content.ANTHROPOLOGY_QUOTES)} اقتباساً"
        )
        await update.message.reply_text(stats, parse_mode="Markdown",
                                        reply_markup=get_reply_keyboard(current_opened))
        return

    # ── رد افتراضي ──
    await update.message.reply_text("الرجاء الضغط على أحد الأزرار للتصفح.",
                                    reply_markup=get_reply_keyboard(current_opened))

# ══════════════════════════════════════════════════════════════════════════════
# ── تشغيل البوت ──────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not TOKEN:
        print("❌ خطأ: يرجى إعداد متغير البيئة TELEGRAM_TOKEN")
        return

    if not GROQ_API_KEY:
        print("⚠️  تنبيه: GROQ_API_KEY غير مضبوط — ميزات الذكاء الاصطناعي معطّلة")

    app = Application.builder().token(TOKEN).build()
    jq  = app.job_queue

    # ── الجدولة اليومية الأصلية (لم تُعدَّل) ──
    # توقيت UTC — الجزائر UTC+1 شتاءً / UTC+2 صيفاً
    # نستخدم UTC+1 ثابت: 9:00ج=8:00ت / 15:00ج=14:00ت / 21:00ج=20:00ت
    jq.run_daily(morning_post, time=datetime.time(hour=8,  minute=0))   # 09:00 جزائر
    jq.run_daily(noon_post,    time=datetime.time(hour=14, minute=0))   # 15:00 جزائر
    jq.run_daily(evening_post, time=datetime.time(hour=20, minute=0))   # 21:00 جزائر

    # ── الجدولة المستقلة للذكاء الاصطناعي — كل ساعة ──
    jq.run_repeating(
        scrape_and_publish_ai_article,
        interval=3600,   # كل 3600 ثانية = ساعة واحدة
        first=120,       # تأخير دقيقتين قبل أول تشغيل عند إقلاع البوت
    )

    # ── تسجيل المعالجات ──
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post",  post_now))
    app.add_handler(CallbackQueryHandler(subscription_callback, pattern="^check_sub$"))

    # معالج منشورات القناة للتعليقات التلقائية
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    # معالج رسائل المستخدمين العادية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت يعمل — قناة @Athar_Anthro جاهزة 💚")
    print("📅 الجدولة: 09:00 | 15:00 | 21:00 جزائر + مقال AI كل ساعة")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
