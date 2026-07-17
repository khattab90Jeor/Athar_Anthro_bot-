# bot.py

import os
import random
import datetime
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# axjdhv_hglpj,n
import content

# qvh_m hgj,;k fHlhk lk Railway
TOKEN = os.getenv("TELEGRAM_TOKEN", "ضع_التوكن_هنا_إذا_كنت_تجرب_على_الحاسوب_محليا")

# 📢 jl vf' hgf,j lfhavm frkhm .,j; hgthqgl ikh
CHANNEL_USERNAME = "@Athar_Anthro"

# phgm fkh_ hgH.vhv hgusgdm dhog prg hg;jhfm
def get_reply_keyboard(opened_section=None):
    btn_cultural = "👇 قسم الثقافي" if opened_section == "cultural" else "📁 علم الإنسان الثقافي"
    btn_biological = "👇 قسم الحيوي" if opened_section == "biological" else "🧬 علم الإنسان الحيوي"
    btn_archaeology = "👇 قسم الآثار" if opened_section == "archaeology" else "🏺 علم الآثار"
    btn_algeria = "👇 قسم الجزائر" if opened_section == "algeria" else "🇩🇿 أنثروبولوجيا الجزائر"
    
    keyboard = []

    if opened_section == "cultural":
        keyboard.append(["📄 عرض محتوى الثقافي", "⬅️ العودة للقائمة"])
    elif opened_section == "biological":
        keyboard.append(["📄 عرض محتوى الحيوي", "⬅️ العودة للقائمة"])
    elif opened_section == "archaeology":
        keyboard.append(["📄 عرض محتوى الآثار", "⬅️ العودة للقائمة"])
    elif opened_section == "algeria":
        keyboard.append(["📜 استكشف أنثروبولوجيا الجزائر", "⬅️ العودة للقائمة"])
    else:
        keyboard = [
            [btn_cultural, btn_biological],
            [btn_archaeology, btn_algeria],
            ["🎲 معلومة عشوائية", "📊 حالة القناة والجدولة"]
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Hlvh hgfkhdm /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['opened_section'] = None
    welcome_text = (
        "🌍 *مرحباً بك في بوت علم الإنسان العالمي والجزائري!*\n\n"
        "تم تصميم الأزرار بالأسفل داخل حقل الكتابة لتسهيل استكشاف الأقسام.\n"
        "📢 *النشر المجدول نشط*: يقوم البوت بالنشر تلقائياً 3 مرات يومياً في القناة.\n\n"
        "🛠️ *للمطور*: يمكنك كتابة الأمر /post للتأكد من النشر الفوري في القناة.\n\n"
        "👇 اختر القسم الذي تريده من لوحة الأزرار بالأسفل:"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_reply_keyboard())

# 🧪 الأمر الجديد /post للتأكد من النشر داخل القناة فوراً
async def test_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fact = random.choice(content.RANDOM_FACTS)
    test_text = (
        f"📢 *منشور تجريبي للتأكد من عمل البوت:*\n\n"
        f"{fact}\n\n"
        f"✨ البوت يعمل بنجاح ومستعد للنشر المجدول تلقائياً!"
    )
    try:
        # إرسال الرسالة للقناة مباشرة
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=test_text, parse_mode='Markdown')
        # إرسال رسالة تأكيد للمستخدم داخل البوت
        await update.message.reply_text(f"✅ تم إرسال المنشور التجريبي بنجاح إلى القناة: {CHANNEL_USERNAME}\nاذهب إلى القناة لتتحقق منه!")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل النشر! تأكد من أنك قمت بإضافة البوت كمشرف (Admin) داخل القناة ومنحه صلاحية النشر.\n\nتفاصيل الخطأ: {e}")

# luhg_ vsh_g hgH.vhv hgusgdm
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_received = update.message.text
    current_opened = context.user_data.get('opened_section', None)

    if text_received == "📁 علم الإنسان الثقافي":
        context.user_data['opened_section'] = "cultural"
        await update.message.reply_text("📂 تم فتح القسم الثقافي، انقر على زر العرض بالأسفل لعرض المحتوى:", reply_markup=get_reply_keyboard("cultural"))
    elif text_received == "🧬 علم الإنسان الحيوي":
        context.user_data['opened_section'] = "biological"
        await update.message.reply_text("📂 تم فتح القسم الحيوي، انقر على زر العرض بالأسفل لعرض المحتوى:", reply_markup=get_reply_keyboard("biological"))
    elif text_received == "🏺 علم الآثار":
        context.user_data['opened_section'] = "archaeology"
        await update.message.reply_text("📂 تم فتح قسم علم الآثار، انقر على زر العرض بالأسفل لعرض المحتوى:", reply_markup=get_reply_keyboard("archaeology"))
    elif text_received == "🇩🇿 أنثروبولوجيا الجزائر":
        context.user_data['opened_section'] = "algeria"
        await update.message.reply_text("📂 تم فتح قسم الجزائر، انقر على زر الاستكشاف بالأسفل لعرض المحتوى:", reply_markup=get_reply_keyboard("algeria"))

    elif text_received in ["👇 قسم الثقافي", "👇 قسم الحيوي", "👇 قسم الآثار", "👇 قسم الجزائر", "⬅️ العودة للقائمة"]:
        context.user_data['opened_section'] = None
        await update.message.reply_text("🔙 تم طي القسم بنجاح، إليك القائمة الرئيسية مجدداً:", reply_markup=get_reply_keyboard())

    elif text_received == "📄 عرض محتوى الثقافي":
        await update.message.reply_text(content.CULTURAL_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📄 عرض محتوى الحيوي":
        await update.message.reply_text(content.BIOLOGICAL_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📄 عرض محتوى الآثار":
        await update.message.reply_text(content.ARCHAEOLOGY_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📜 استكشف أنثروبولوجيا الجزائر":
        await update.message.reply_text(content.ALGERIA_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))

    elif text_received == "🎲 معلومة عشوائية":
        fact = random.choice(content.RANDOM_FACTS)
        await update.message.reply_text(f"🎲 *معلومة أنثروبولوجية:*\n\n{fact}", parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📊 حالة القناة والجدولة":
        stats_text = (
            f"📊 *حالة النظام والربط:*\n\n"
            f"• القناة المرتبطة: {CHANNEL_USERNAME}\n"
            f"• نظام الجدولة: يعمل تلقائياً بانتظام 3 مرات يومياً.\n"
            f"• المواعيد المحددة: 09:00 صباحاً | 15:00 عصراً | 21:00 مساءً."
        )
        await update.message.reply_text(stats_text, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    else:
        await update.message.reply_text("الرجاء الضغط على الأزرار السفلية الظاهرة لديك للتصفح الفرعي.", reply_markup=get_reply_keyboard(current_opened))

# 📅 dhgm hgkhv hgl_d,g hgjrhdd fhog hg;khm lfhvhm
async def send_daily_fact(context: ContextTypes.DEFAULT_TYPE) -> None:
    fact = random.choice(content.RANDOM_FACTS)
    broadcast_text = (
        f"📢 *معلومة أنثروبولوجية يومية:*\n\n"
        f"{fact}\n\n"
        f"✨ تابعوا قناتنا للمزيد من أسرار علم الإنسان!"
    )
    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=broadcast_text, parse_mode='Markdown')
    except Exception as e:
        print(f"خطأ أثناء النشر في القناة: {e}")

def main():
    if not TOKEN or TOKEN == "ضع_التوكن_هنا_إذا_كنت_تجرب_على_الحاسوب_محليا":
        print("خطأ: يرجى إعداد متغير البيئة TELEGRAM_TOKEN")
        return

    application = Application.builder().token(TOKEN).build()
    job_queue = application.job_queue

    # hgj_d,g 3 lvhj d,ldh
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=9, minute=0, second=0))
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=15, minute=0, second=0))
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=21, minute=0, second=0))

    # j_dg hgH,hlv
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("post", test_post)) # تسجيل الأمر التجريبي الجديد
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت والجدولة يعملان الآن بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
