import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
import audit_tools

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
        InlineKeyboardButton("🤖 فاحص المتابعين الوهميين", callback_data="fake_audit"),
        InlineKeyboardButton("💳 رصيدي وباقة VIP", callback_data="credits")
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
        "أداة المحترفين وأصحاب المتاجر الأولى والأقوى على تيليجرام لتحليل الحسابات وكشف المخفي!\n"
        "لديك (3) محاولات فحص مجانية كهدية ترحيبية 🎁\n\n"
        "👇 اختر أداة الفحص التي تحتاجها الآن:"
    )
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    msg_id = call.message.message_id
    
    # التحقق من الرصيد قبل أي فحص
    if call.data in ["osint", "shadowban", "fake_audit"]:
        if not database.check_can_scan(user_id):
            bot.answer_callback_query(call.id, "نفد رصيدك من الفحوصات المجانية! اشترك بالـ VIP", show_alert=True)
            return

    if call.data == "osint":
        user_states[user_id] = "WAIT_OSINT"
        bot.edit_message_text("🕵️ أرسل اليوزر (Username) الذي تريد كشف حساباته في المواقع الأخرى:\nمثال: @elonmusk", call.message.chat.id, msg_id)
        
    elif call.data == "shadowban":
        user_states[user_id] = "WAIT_SHADOWBAN"
        bot.edit_message_text("📉 أرسل رابط حساب التيك توك أو تويتر لتحليل حظر الإكسبلور والشادوبان:", call.message.chat.id, msg_id)
        
    elif call.data == "fake_audit":
        user_states[user_id] = "WAIT_FAKE_AUDIT"
        bot.edit_message_text("🤖 أرسل يوزر المشهور أو المتجر لفحص نسبة المتابعين الوهميين ومدى مصداقيته:", call.message.chat.id, msg_id)
        
    elif call.data == "credits":
        user = database.get_or_create_user(user_id, "")
        if user["is_vip"]:
            status = "👑 مشترك VIP (فحوصات لا محدودة)"
        else:
            status = f"🎟️ الفحوصات المتبقية: {user['remaining_scans']}\nلشراء فحص لا محدود طوال الشهر تواصل مع الإدارة!"
            
        bot.edit_message_text(f"💳 **معلومات الرصيد:**\n\n{status}", call.message.chat.id, msg_id, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    target = message.text.strip()
    state = user_states.get(user_id, "IDLE")
    
    if state in ["WAIT_OSINT", "WAIT_SHADOWBAN", "WAIT_FAKE_AUDIT"]:
        # الخصم من الرصيد
        if not database.consume_scan(user_id):
            bot.send_message(user_id, "❌ رصيدك لا يسمح بإجراء الفحص. اشترك بالباقة المدفوعة.")
            user_states[user_id] = "IDLE"
            return
            
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
    bot.infinity_polling()
