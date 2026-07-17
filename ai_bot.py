# ai_bot.py — البوت الذكي المستقل لقناة أثر الأنثروبولوجيا
#
# الوظائف:
#   1. الرد على رسائل /start والمحادثات الخاصة بذكاء اصطناعي أنثروبولوجي
#   2. الاستماع لمجموعة النقاش والرد تلقائياً على منشورات القناة بتعليق Groq
#   3. نشر مقالات Phys.org مترجمة كل 30 دقيقة في القناة
#
# متغيرات البيئة المطلوبة:
#   AI_BOT_TOKEN     — توكن البوت الذكي (مختلف عن TELEGRAM_TOKEN)
#   GROQ_API_KEY     — مفتاح Groq
#   CHANNEL_USERNAME — اختياري، الافتراضي: @Athar_Anthro

import os
import asyncio
import time
import requests

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️ beautifulsoup4 غير مثبّت — سحب Phys.org معطّل")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ groq غير مثبّت — ميزات الذكاء الاصطناعي معطّلة")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── إعدادات ─────────────────────────────────────────────────────────────────
AI_BOT_TOKEN       = os.getenv("AI_BOT_TOKEN", "")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
CHANNEL_USERNAME   = os.getenv("CHANNEL_USERNAME", "@Athar_Anthro")
CHANNEL_NAME_LOWER = CHANNEL_USERNAME.lstrip("@").lower()

# ── ذاكرة ────────────────────────────────────────────────────────────────────
_groq_client: "Groq | None" = None
_last_published_url: str    = ""

# ══════════════════════════════════════════════════════════════════════════════
# ── عميل Groq ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def get_groq_client():
    global _groq_client
    if not GROQ_AVAILABLE or not GROQ_API_KEY:
        return None
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

# ══════════════════════════════════════════════════════════════════════════════
# ── وظائف Groq (sync — تُستدعى من asyncio.to_thread) ────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _sync_answer_question(user_text: str) -> str:
    """يُجيب على سؤال مباشر من المستخدم في المحادثة الخاصة."""
    client = get_groq_client()
    if not client:
        return "⚠️ خدمة الذكاء الاصطناعي غير متاحة حالياً، تحقق من GROQ_API_KEY."
    prompt = (
        "أنت أستاذ متخصص في علم الإنسان (الأنثروبولوجيا) وعلم الآثار، "
        "تعمل مساعداً ذكياً لقناة تيليغرام أنثروبولوجية عربية. "
        "أسلوبك: علمي دقيق مع لمسة إنسانية دافئة، تستشهد بأمثلة وحضارات حقيقية.\n\n"
        f"سؤال المستخدم: {user_text}\n\n"
        "أجب بالعربية الفصحى في 80 إلى 150 كلمة، مباشرةً دون مقدمة."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.75,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq_answer] ❌ {e}")
        return "❌ تعذّر الحصول على إجابة، حاول مرة أخرى."


def _sync_generate_comment(post_text: str) -> str | None:
    """يُولّد تعليقاً أنثروبولوجياً ذكياً على منشور القناة في المجموعة."""
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
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.8,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq_comment] ❌ {e}")
        return None


def _sync_translate_article(title: str, summary: str) -> str | None:
    """يُترجم مقالاً علمياً إلى منشور أنثروبولوجي عربي."""
    client = get_groq_client()
    if not client:
        return None
    prompt = (
        "أنت خبير في علم الإنسان (الأنثروبولوجيا) وكاتب عربي متمكن. "
        "لديك المقال العلمي التالي باللغة الإنجليزية:\n\n"
        f"العنوان: {title}\n\n"
        f"المحتوى: {summary}\n\n"
        "المطلوب: اكتب منشوراً علمياً جذاباً بالعربية الفصحى لقناة تيليغرام متخصصة في الأنثروبولوجيا.\n"
        "- ابدأ بعنوان مشوق يحتوي إيموجي مناسب\n"
        "- اشرح الاكتشاف بأسلوب علمي شيق\n"
        "- أضف سياقاً أنثروبولوجياً يربط الموضوع بالإنسانية الكبرى\n"
        "- اختم بجملة تُلهم التفكير\n"
        "- الطول المثالي: 150 إلى 250 كلمة\n\n"
        "اكتب المنشور مباشرة دون مقدمة أو شرح إضافي."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.75,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq_translate] ❌ {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# ── Scraping Phys.org ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

PHYS_URL = "https://phys.org/anthropology-news/"
HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def _sync_fetch_image(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        if resp.status_code == 200 and len(resp.content) < 9 * 1024 * 1024:
            return resp.content
    except Exception as e:
        print(f"[fetch_image] {e}")
    return None


def _sync_scrape_phys_article() -> dict | None:
    if not BS4_AVAILABLE:
        return None
    try:
        resp = requests.get(PHYS_URL, timeout=15, headers=HEADERS)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        article_link = ""
        article_title = ""

        for tag in soup.select("article h3 a, .sorted-article-title a, .news-title a, h3.mb-1 a"):
            href = tag.get("href", "")
            if href and "/news/" in href:
                article_link  = href if href.startswith("http") else "https://phys.org" + href
                article_title = tag.get_text(strip=True)
                break

        if not article_link:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/news/" in href and href.endswith(".html"):
                    article_link  = href if href.startswith("http") else "https://phys.org" + href
                    article_title = a.get_text(strip=True)
                    break

        if not article_link:
            print("[phys_scrape] لم يُعثر على مقال")
            return None

        art = requests.get(article_link, timeout=15, headers=HEADERS)
        if art.status_code != 200:
            return None

        art_soup = BeautifulSoup(art.text, "html.parser")

        h1 = art_soup.find("h1")
        if h1:
            article_title = h1.get_text(strip=True)

        parts = []
        for p in art_soup.select("article p, .article-main p, .text-block p"):
            t = p.get_text(strip=True)
            if len(t) > 60:
                parts.append(t)
            if len(parts) >= 3:
                break
        summary = " ".join(parts) if parts else article_title

        image_url = None
        for img in art_soup.select("article img, .article-main img, figure img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and src.startswith("http") and any(ext in src for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                image_url = src
                break

        return {
            "url": article_link,
            "title": article_title,
            "summary": summary[:2000],
            "image_url": image_url,
        }

    except Exception as e:
        print(f"[phys_scrape] ❌ {e}")
        return None


def _strip_md(text: str) -> str:
    return text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

# ══════════════════════════════════════════════════════════════════════════════
# ── مهمة النشر المجدولة ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_and_publish(context: ContextTypes.DEFAULT_TYPE) -> None:
    """تُشغَّل كل 30 دقيقة — تسحب مقالاً جديداً وتنشره في القناة."""
    global _last_published_url

    if not GROQ_API_KEY:
        print("[ai_scraper] GROQ_API_KEY غير مضبوط")
        return

    print("[ai_scraper] 🔄 بدء سحب مقال من Phys.org ...")
    article = await asyncio.to_thread(_sync_scrape_phys_article)

    if not article:
        print("[ai_scraper] ❌ لم يُعثر على مقال")
        return

    if article["url"] == _last_published_url:
        print(f"[ai_scraper] ⏭️ نفس المقال السابق: {article['url']}")
        return

    print(f"[ai_scraper] 📰 مقال جديد: {article['title']}")

    arabic_text = await asyncio.to_thread(
        _sync_translate_article, article["title"], article["summary"]
    )
    if not arabic_text:
        print("[ai_scraper] ❌ فشل Groq في الترجمة")
        return

    header = (
        "🤖 اكتشاف علمي جديد — مباشرة من المجلات العالمية\n"
        "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n\n"
    )
    footer = (
        f"\n\n🔗 المصدر: {article['url']}\n"
        "〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n"
        f"📡 قناة أثر الأنثروبولوجيا | {CHANNEL_USERNAME}"
    )
    full_text = header + arabic_text + footer
    caption   = full_text[:1024]

    published = False

    image_url = article.get("image_url")
    if image_url:
        img_bytes = await asyncio.to_thread(_sync_fetch_image, image_url)
        if img_bytes:
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_USERNAME, photo=img_bytes, caption=caption
                )
                published = True
                print("[ai_scraper] ✅ نُشر بصورة")
            except Exception as e:
                print(f"[ai_scraper photo] {e}")

    if not published:
        try:
            await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=full_text)
            published = True
            print("[ai_scraper] ✅ نُشر نصاً")
        except Exception as e:
            print(f"[ai_scraper text] {e}")

    if not published:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME, text=_strip_md(full_text[:4000])
            )
            published = True
            print("[ai_scraper] ✅ نُشر نصاً مقتصراً")
        except Exception as e:
            print(f"[ai_scraper stripped] ❌ {e}")

    if published:
        _last_published_url = article["url"]
    else:
        print("[ai_scraper] ❌ فشل النشر")

# ══════════════════════════════════════════════════════════════════════════════
# ── معالجات المحادثة الخاصة ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

START_TEXT = (
    "مرحباً بك! 👋\n\n"
    "أنا *أثر الذكي* — مساعدك الأنثروبولوجي الذكي لقناة *أثر الأنثروبولوجيا*.\n\n"
    "🔬 *ما الذي أفعله؟*\n"
    "• أرد على أسئلتك في علم الإنسان والآثار والحضارات\n"
    "• أُعلّق تلقائياً على منشورات القناة في مجموعة النقاش\n"
    "• أنشر اكتشافات علمية جديدة مترجمة كل 30 دقيقة في القناة\n\n"
    "💬 *كيف تستخدمني؟*\n"
    "اكتب سؤالك أو موضوعاً تريد معرفة المزيد عنه وسأجيبك فوراً!\n\n"
    f"📡 تابع القناة: {CHANNEL_USERNAME}"
)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يرد على /start في المحادثة الخاصة."""
    await update.message.reply_text(START_TEXT, parse_mode="Markdown")


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يرد على أي رسالة خاصة بذكاء اصطناعي أنثروبولوجي."""
    msg = update.message
    if not msg or not msg.text:
        await msg.reply_text("أرسل سؤالاً نصياً وسأجيبك! 🔬")
        return

    user_text = msg.text.strip()
    print(f"[private_handler] 💬 سؤال: {user_text[:80]}")

    # مؤشر الكتابة
    await context.bot.send_chat_action(
        chat_id=msg.chat_id, action="typing"
    )

    answer = await asyncio.to_thread(_sync_answer_question, user_text)
    await msg.reply_text(answer)
    print(f"[private_handler] ✅ أجاب على: {user_text[:40]}")

# ══════════════════════════════════════════════════════════════════════════════
# ── معالج مجموعة النقاش — الرد على منشورات القناة ───────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _is_channel_forward(msg) -> bool:
    """
    يتحقق إذا كانت الرسالة منشور قناة أُعيد توجيهه للمجموعة المرتبطة.

    الحالات المدعومة:
      ① is_automatic_forward=True + sender_chat  ← منشورات القناة التلقائية (الأشيع)
      ② forward_from_chat                        ← توجيه يدوي قديم
      ③ forward_origin.chat                      ← PTB 21+ توجيه يدوي جديد
    """
    # ① الحالة الأشيع: إعادة توجيه تلقائية للمجموعة المرتبطة بالقناة
    if getattr(msg, "is_automatic_forward", False):
        sender_chat = getattr(msg, "sender_chat", None)
        if sender_chat:
            username = (getattr(sender_chat, "username", "") or "").lower()
            if username == CHANNEL_NAME_LOWER:
                return True
            if not username:
                return True   # لا يمكن التحقق من الاسم → نقبل (المصدر تلقائي)
        else:
            return True       # is_automatic_forward بدون sender_chat → نقبل

    # ② توجيه يدوي — واجهة قديمة
    fwd_chat = getattr(msg, "forward_from_chat", None)
    if fwd_chat:
        username = (getattr(fwd_chat, "username", "") or "").lower()
        if username == CHANNEL_NAME_LOWER:
            return True

    # ③ توجيه يدوي — PTB 21+
    fwd_origin = getattr(msg, "forward_origin", None)
    if fwd_origin:
        origin_chat = getattr(fwd_origin, "chat", None)
        if origin_chat:
            username = (getattr(origin_chat, "username", "") or "").lower()
            if username == CHANNEL_NAME_LOWER:
                return True

    return False


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يستمع لمجموعة النقاش.
    عندما يرى منشوراً مُعاد توجيهه من القناة → يرد بتعليق Groq.
    """
    msg = update.message
    if not msg:
        return

    # تجاهل رسائل البوتات (بما فيها رسائل هذا البوت نفسه)
    if msg.from_user and msg.from_user.is_bot:
        return

    if not _is_channel_forward(msg):
        return

    post_text = msg.text or msg.caption or "منشور أنثروبولوجي"
    print(f"[group_handler] 📩 منشور قناة مُعاد توجيهه id={msg.message_id}")

    # مؤشر الكتابة في المجموعة
    try:
        await context.bot.send_chat_action(
            chat_id=msg.chat_id, action="typing"
        )
    except Exception:
        pass

    comment = await asyncio.to_thread(_sync_generate_comment, post_text)
    if not comment:
        print("[group_handler] ❌ Groq لم يُولّد تعليقاً")
        return

    try:
        await msg.reply_text(comment)
        print(f"[group_handler] ✅ تعليق نُشر ردًا على {msg.message_id}")
    except Exception as e:
        print(f"[group_handler] ❌ {e}")
        try:
            await msg.reply_text(_strip_md(comment))
            print("[group_handler] ✅ تعليق نُشر (بدون تنسيق)")
        except Exception as e2:
            print(f"[group_handler] ❌ فشل كل المحاولات: {e2}")

# ══════════════════════════════════════════════════════════════════════════════
# ── تشغيل البوت ──────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _build_app() -> Application:
    app = Application.builder().token(AI_BOT_TOKEN).build()
    jq  = app.job_queue

    # جدولة النشر كل 30 دقيقة
    if BS4_AVAILABLE and GROQ_API_KEY:
        jq.run_repeating(scrape_and_publish, interval=1800, first=60)
        print("🤖 جدولة AI مفعّلة — مقال Phys.org كل 30 دقيقة")

    # ── معالجات المحادثة الخاصة ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start", handle_start,
                                   filters=filters.ChatType.PRIVATE))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_private_message,
    ))

    # ── معالج مجموعة النقاش ─────────────────────────────────────────────────
    group_filter = filters.ChatType.SUPERGROUP | filters.ChatType.GROUP
    app.add_handler(MessageHandler(group_filter, handle_group_message))

    return app


def main():
    if not AI_BOT_TOKEN:
        print("❌ AI_BOT_TOKEN غير مضبوط — أوقف ai_bot.py")
        return

    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY غير مضبوط — ميزات AI معطّلة")

    print(f"🤖 ai_bot.py يبدأ — القناة: {CHANNEL_USERNAME}")

    # إعادة محاولة تلقائية عند Conflict (نسختان في آنٍ واحد أثناء النشر)
    for attempt in range(1, 6):
        app = _build_app()
        try:
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
            )
            break  # خرج بشكل طبيعي
        except Exception as e:
            if "Conflict" in str(e):
                wait = attempt * 15
                print(f"[ai_bot] ⚠️ Conflict — محاولة {attempt}/5، انتظار {wait}ث ...")
                time.sleep(wait)
            else:
                print(f"[ai_bot] ❌ خطأ: {e}")
                raise


if __name__ == "__main__":
    main()
