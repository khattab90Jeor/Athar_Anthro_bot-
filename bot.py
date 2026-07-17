# bot.py

import os
import random
import datetime
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# استيراد المحتوى
import content

# قراءة التوكن بأمان من Railway
TOKEN = os.getenv("TELEGRAM_TOKEN", "ضع_التوكن_هنا_إذا_كنت_تجرب_على_الحاسوب_محليا")

# 📢 تم ربط البوت مباشرة بقناة زوجتك الفاضلة هنا
CHANNEL_USERNAME = "@Athar_Dz_Islamic"

# دالة بناء الأزرار العادية داخل حقل الكتابة (تفتح وتختفي شجرياً)
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
        # تصميم الأزرار السفلية الافتراضي (زرين في كل صف كصورتك تماماً)
        keyboard = [
            [btn_cultural, btn_biological],
            [btn_archaeology, btn_algeria],
            ["🎲 معلومة عشوائية", "📊 حالة القناة والجدولة"]
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# أمر البداية /start للأعضاء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['opened_section'] = None
    welcome_text = (
        "🌍 *مرحباً بك في بوت علم الإنسان العالمي والجزائري!*\n\n"
        "تم تصميم الأزرار بالأسفل داخل حقل الكتابة لتسهيل استكشاف الأقسام.\n"
        "📢 *النشر المجدول نشط*: يقوم البوت بالنشر تلقائياً 3 مرات يومياً في القناة.\n\n"
        "👇 اختر القسم الذي تريده من لوحة الأزرار بالأسفل:"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_reply_keyboard())

# معالج رسائل الأزرار السفلية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text_received = update.message.text
    current_opened = context.user_data.get('opened_section', None)

    # فتح الفروع
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

    # طي الأزرار والعودة
    elif text_received in ["👇 قسم الثقافي", "👇 قسم الحيوي", "👇 قسم الآثار", "👇 قسم الجزائر", "⬅️ العودة للقائمة"]:
        context.user_data['opened_section'] = None
        await update.message.reply_text("🔙 تم طي القسم بنجاح، إليك القائمة الرئيسية مجدداً:", reply_markup=get_reply_keyboard())

    # عرض البيانات
    elif text_received == "📄 عرض محتوى الثقافي":
        await update.message.reply_text(content.CULTURAL_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📄 عرض محتوى الحيوي":
        await update.message.reply_text(content.BIOLOGICAL_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📄 عرض محتوى الآثار":
        await update.message.reply_text(content.ARCHAEOLOGY_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))
    elif text_received == "📜 استكشف أنثروبولوجيا الجزائر":
        await update.message.reply_text(content.ALGERIA_CONTENT, parse_mode='Markdown', reply_markup=get_reply_keyboard(current_opened))

    # ميزات عامة
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

# 📅 دالة النشر المجدول التلقائي داخل القناة مباشرة
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

# تشغيل البوت والجدولة
def main():
    if not TOKEN or TOKEN == "ضع_التوكن_هنا_إذا_كنت_تجرب_على_الحاسوب_محليا":
        print("خطأ: يرجى إعداد متغير البيئة TELEGRAM_TOKEN")
        return

    application = Application.builder().token(TOKEN).build()
    job_queue = application.job_queue

    # إعداد مواعيد النشر الثلاثة يومياً
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=9, minute=0, second=0))
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=15, minute=0, second=0))
    job_queue.run_daily(send_daily_fact, time=datetime.time(hour=21, minute=0, second=0))

    # تسجيل الأوامر والرسائل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت والجدولة لقناة زوجتك يعملان الآن بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
