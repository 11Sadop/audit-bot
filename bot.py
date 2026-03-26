import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
import audit_tools

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
        InlineKeyboardButton("🕵️ المحقق: كشف حسابات ยوزر (OSINT)", callback_data="osint"),
        InlineKeyboardButton("📉 فحص حظر الإكسبلور والشادوبان", callback_data="shadowban"),
        InlineKeyboardButton("🤖 فاحص المتابعين الوهميين", callback_data="fake_audit")
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
    
        bot.edit_message_text("🤖 أرسل يوزر المشهور أو المتجر لفحص نسبة المتابعين الوهميين ومدى مصداقيته:", call.message.chat.id, msg_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    target = message.text.strip()
    state = user_states.get(user_id, "IDLE")
    
    if state in ["WAIT_OSINT", "WAIT_SHADOWBAN", "WAIT_FAKE_AUDIT"]:
        loading_msg = bot.send_message(user_id, "⏳ جاري الاتصال بقواعد البيانات وتحليل الخوارزميات... (قد يستغرق 10 ثواني)")
        
        try:
            if state == "WAIT_OSINT":
                report = audit_tools.osint_search(target.replace('@', ''))
            elif state == "WAIT_SHADOWBAN":
                report = audit_tools.shadowban_check("TikTok / Twitter", target)
            elif state == "WAIT_FAKE_AUDIT":
                report = audit_tools.fake_followers_audit("منصات التواصل", target)
                
            bot.edit_message_text(report, user_id, loading_msg.message_id, parse_mode="Markdown")
            
        except Exception as e:
            bot.edit_message_text(f"❌ حدث خطأ برمجى أثناء التحليل: {e}", user_id, loading_msg.message_id)
            
        user_states[user_id] = "IDLE"
        bot.send_message(user_id, "هل تريد إجراء فحص آخر؟", reply_markup=get_main_menu())

print("✅ تم تشغيل بوت المحقق والتحليل الشامل بنجاح...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception as e:
        pass
    bot.infinity_polling()
