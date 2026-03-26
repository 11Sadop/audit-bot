import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
import audit_tools
import downloader

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive and working!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ----------------- الإعدادات الأساسية -----------------
# التوكن يتم سحبه تلقائياً من إعدادات سريفر (Render) للحماية
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

bot = telebot.TeleBot(BOT_TOKEN)
database.init_db()

# لتتبع حالة المستخدم (ما الذي يتوقعه البوت من المستخدم؟)
user_states = {}

def get_main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📋 استخبارات وتفاصيل حساب تيك توك (حقيقي)", callback_data="osint"),
        InlineKeyboardButton("📉 فحص حظر الإكسبلور والشادوبان", callback_data="shadowban"),
        InlineKeyboardButton("🤖 فاحص المتابعين الوهميين (Live)", callback_data="fake_audit"),
        InlineKeyboardButton("🔗 فحص الربط المخفي (قبل الشراء)", callback_data="hidden_links"),
        InlineKeyboardButton("💬 كاشف التعليقات الوهمية (Spam)", callback_data="comment_spam"),
        InlineKeyboardButton("📥 تحميل فيديو (بدون حقوق)", callback_data="download_video"),
        InlineKeyboardButton("🔇 تحميل فيديو (بدون موسيقى)", callback_data="download_video_no_music")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    database.get_or_create_user(user_id, username)
    user_states[user_id] = "IDLE"
    
    welcome = (
        f"أهلاً بك {username} في **بوت المحقق الشامل للأدوات الذكية** 💻\n\n"
        "أداة المحترفين وأصحاب المتاجر الأولى والأقوى على تيليجرام لتحليل الحسابات وكشف المخفي!\n\n"
        "👇 اختر أداة الفحص المجانية التي تحتاجها الآن:"
    )
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    msg_id = call.message.message_id
    
    if call.data == "osint":
        user_states[user_id] = "WAIT_OSINT"
        bot.edit_message_text("🕵️ أرسل اليوزر (Username) الذي تريد كشف حساباته في المواقع الأخرى:\nمثال: @elonmusk", call.message.chat.id, msg_id)
        
    elif call.data == "shadowban":
        user_states[user_id] = "WAIT_SHADOWBAN"
        bot.edit_message_text("📉 أرسل رابط حساب التيك توك أو تويتر لتحليل حظر الإكسبلور والشادوبان:", call.message.chat.id, msg_id)
        
    elif call.data == "fake_audit":
        user_states[user_id] = "WAIT_FAKE_AUDIT"
        bot.edit_message_text("🤖 أرسل اليوزر الخاص بحساب تيك توك (بدون @) لأسحب إحصائياته الحقيقية وأفحص نسبة المتابعين الوهميين بدقة:", call.message.chat.id, msg_id, parse_mode="Markdown")
        
    elif call.data == "hidden_links":
        user_states[user_id] = "WAIT_HIDDEN_LINKS"
        bot.edit_message_text("🔗 أرسل اليوزر (Username) لفحص قيود الربط المخفي (أبل، جوجل، فيسبوك) ومخاطر استرجاع الحساب:", call.message.chat.id, msg_id)

    elif call.data == "comment_spam":
        user_states[user_id] = "WAIT_COMMENT_SPAM"
        bot.edit_message_text("💬 أرسل رابط أقوى فيديو في الحساب لفحص الذكاء الاصطناعي للتعليقات وكشف (قروبات الدعم الوهمي) والمجاملات:", call.message.chat.id, msg_id)
        
    elif call.data == "download_video":
        user_states[user_id] = "WAIT_VIDEO_DL"
        bot.edit_message_text("📥 أرسل لي رابط الفيديو من (تيك توك، انستقرام، تويتر، يوتيوب Shorts):\nوسأقوم بتحميله لك بدون حقوق أو علامة مائية:", call.message.chat.id, msg_id)

    elif call.data == "download_video_no_music":
        user_states[user_id] = "WAIT_VIDEO_NO_MUSIC"
        bot.edit_message_text("🔇 أرسل الرابط هنا، وسأقوم بسحب الفيديو الأصلي وصقله (بدون موسيقى أو أغاني) تماماً لتتجنب الذنوب والمخالفات:", call.message.chat.id, msg_id)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    target = message.text.strip()
    state = user_states.get(user_id, "IDLE")
    
    if state in ["WAIT_OSINT", "WAIT_SHADOWBAN", "WAIT_FAKE_AUDIT", "WAIT_HIDDEN_LINKS", "WAIT_COMMENT_SPAM"]:
        loading_msg = bot.send_message(user_id, "⏳ جاري الاتصال بقواعد البيانات وتحليل الخوارزميات... (قد يستغرق 10 ثواني)")
        
        try:
            if state == "WAIT_OSINT":
                report = audit_tools.real_tiktok_info(target.replace('@', '').strip())
            elif state == "WAIT_SHADOWBAN":
                report = audit_tools.shadowban_check("TikTok / Twitter", target)
            elif state == "WAIT_FAKE_AUDIT":
                report = audit_tools.real_fake_followers_audit(target.replace('@', '').strip())
            elif state == "WAIT_HIDDEN_LINKS":
                report = audit_tools.hidden_links_check(target.replace('@', ''))
            elif state == "WAIT_COMMENT_SPAM":
                report = audit_tools.comment_spam_check(target)
                
            bot.edit_message_text(report, user_id, loading_msg.message_id, parse_mode="Markdown")
            
        except Exception as e:
            bot.edit_message_text(f"❌ حدث خطأ برمجى أثناء التحليل: {e}", user_id, loading_msg.message_id)
            
        user_states[user_id] = "IDLE"
        bot.send_message(user_id, "هل تريد إجراء فحص آخر؟", reply_markup=get_main_menu())
        return

    if state == "WAIT_VIDEO_DL":
        loading_msg = bot.send_message(user_id, "⏳ جاري استخراج الفيديو الأصلي بدون علامة مائية... الرجاء الانتظار دقيقة.")
        
        try:
            video_path = downloader.download_video_no_watermark(target)
            if video_path:
                with open(video_path, 'rb') as video_file:
                    bot.send_video(user_id, video_file, caption="✅ تم التحميل بالدقة الأصلية وبدون حقوق!\n@YourBotUsername")
                os.remove(video_path)
                bot.delete_message(user_id, loading_msg.message_id)
            else:
                bot.edit_message_text("❌ عذراً، لم أتمكن من تحميل هذا الرابط. قد يكون الحساب خاصاً أو الرابط غير مدعوم.", user_id, loading_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {e}", user_id, loading_msg.message_id)
            
        user_states[user_id] = "IDLE"
        bot.send_message(user_id, "هل تريد خدمة أخرى؟", reply_markup=get_main_menu())
        return

    if state == "WAIT_VIDEO_NO_MUSIC":
        loading_msg = bot.send_message(user_id, "⏳ جاري استخراج الفيديو، وإزالة الموسيقى الأصلية تماماً... الرجاء الانتظار دقيقة.")
        
        try:
            video_path = downloader.download_video_no_music(target)
            if video_path:
                with open(video_path, 'rb') as video_file:
                    bot.send_video(user_id, video_file, caption="✅ تم التحميل (بدون موسيقى) وبدون حقوق!\n@YourBotUsername")
                os.remove(video_path)
                bot.delete_message(user_id, loading_msg.message_id)
            else:
                bot.edit_message_text("❌ عذراً، لم أتمكن من تحميل هذا الرابط. قد يكون الحساب خاصاً أو الرابط لا يدعم هذه الميزة.", user_id, loading_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {e}", user_id, loading_msg.message_id)
            
        user_states[user_id] = "IDLE"
        bot.send_message(user_id, "هل تريد خدمة أخرى؟", reply_markup=get_main_menu())
        return

print("✅ تم تشغيل بوت المحقق والتحليل الشامل بنجاح...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception as e:
        pass
    bot.infinity_polling()
