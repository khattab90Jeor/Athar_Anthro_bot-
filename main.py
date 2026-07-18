# main.py — نقطة التشغيل الموحدة: يُشغّل كلا البوتين في عملية asyncio واحدة
#
# السبب: Railway يشغّل عملية واحدة افتراضياً من Procfile.
# الحل: نبني كلا التطبيقين ونشغّلهما بـ asyncio.gather بدلاً من Procfile مزدوج.
#
# متغيرات البيئة المطلوبة:
#   TELEGRAM_TOKEN   — بوت القائمة الرئيسي
#   AI_BOT_TOKEN     — بوت الردود الذكي
#   GROQ_API_KEY     — مفتاح Groq للذكاء الاصطناعي

import asyncio
import signal
import sys

from telegram import Update


async def _run() -> None:
    # ── استيراد البوتين ──────────────────────────────────────────────────────
    try:
        from bot import build_app as build_main
    except Exception as e:
        print(f"[main] ❌ فشل استيراد bot.py: {e}")
        build_main = None

    try:
        from ai_bot import build_app as build_ai
    except Exception as e:
        print(f"[main] ❌ فشل استيراد ai_bot.py: {e}")
        build_ai = None

    if not build_main and not build_ai:
        print("[main] ❌ لا يوجد بوت صالح للتشغيل — تحقق من متغيرات البيئة")
        return

    # ── بناء التطبيقات ───────────────────────────────────────────────────────
    apps = []
    if build_main:
        try:
            app_main = build_main()
            apps.append(("bot_main", app_main))
            print("✅ bot.py جاهز")
        except Exception as e:
            print(f"[main] ⚠️ bot.py لم يُبنَ: {e}")

    if build_ai:
        try:
            app_ai = build_ai()
            apps.append(("bot_ai", app_ai))
            print("✅ ai_bot.py جاهز")
        except Exception as e:
            print(f"[main] ⚠️ ai_bot.py لم يُبنَ: {e}")

    if not apps:
        print("[main] ❌ لا توجد تطبيقات صالحة")
        return

    # ── إشارة الإيقاف ────────────────────────────────────────────────────────
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # Windows

    # ── تشغيل كلا البوتين داخل async context manager ────────────────────────
    async def _start_all():
        # initialize (الـ context manager)
        for name, app in apps:
            await app.initialize()
            print(f"[main] ▶️ {name} initialize ✓")

        for name, app in apps:
            await app.start()
            print(f"[main] ▶️ {name} start ✓")

        for name, app in apps:
            drop = (name == "bot_ai")   # ai_bot يتجاهل الرسائل القديمة
            await app.updater.start_polling(
                drop_pending_updates=drop,
                allowed_updates=Update.ALL_TYPES,
            )
            print(f"[main] 📡 {name} polling ✓")

        print("\n🚀 كلا البوتين يعملان الآن!\n"
              "   • bot_main  — القائمة والجدولة اليومية\n"
              "   • bot_ai    — الردود الذكية والمقالات\n")

        await stop.wait()

        # ── إيقاف نظيف ──────────────────────────────────────────────────────
        print("[main] 🛑 إيقاف ...")
        for name, app in reversed(apps):
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
                print(f"[main] ✅ {name} أُوقف")
            except Exception as e:
                print(f"[main] ⚠️ {name} خطأ أثناء الإيقاف: {e}")

    await _start_all()


def main():
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n[main] ⌨️ Ctrl+C — تم الإيقاف")
    except Exception as e:
        print(f"[main] ❌ خطأ قاتل: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
