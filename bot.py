import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
import database

# --- Dummy Server for Render ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Auction Bot Running")
    def log_message(self, format, *args):
        pass

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', int(os.environ.get('PORT', 10000))), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- Bot Setup ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)

# Save owner ID to database
database.set_config("owner_id", str(OWNER_ID))

# --- State Machine ---
user_states = {}
admin_auction_data = {}

# --- Helper: Currency Symbol ---
def cur(currency):
    return "ريال" if currency == "SAR" else "$"

# --- Helper: Build Auction Message ---
def build_auction_text(auction):
    c = cur(auction['currency'])
    bidder_name = "لا يوجد بعد"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
        bidder_name = database.get_username(auction['highest_bidder'])
        # تشفير جزئي للاسم
        if len(bidder_name) > 3:
            bidder_name = bidder_name[:3] + "***"
    
    status_emoji = "🟢 جاري" if auction['status'] == 'active' else "🔴 منتهي"
    
    text = f"🏷️ **مزاد رقم #{auction['id']}**\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"📦 **السلعة:** {auction['title']}\n"
    if auction.get('description'):
        text += f"📝 **الوصف:** {auction['description']}\n"
    text += f"💰 **سعر الافتتاح:** {auction['start_price']:,} {c}\n"
    text += f"📈 **أقل زيادة:** {auction['min_increment']:,} {c}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"🔥 **أعلى سومة حالياً:** {auction['current_price']:,} {c}\n"
    text += f"👤 **صاحب أعلى سومة:** {bidder_name}\n"
    text += f"📊 **الحالة:** {status_emoji}\n"
    return text

def build_bid_buttons(auction):
    markup = InlineKeyboardMarkup()
    if auction['status'] != 'active':
        return markup
    inc = auction['min_increment']
    aid = auction['id']
    markup.row(
        InlineKeyboardButton(f"⬆️ +{inc:,}", callback_data=f"bid_{aid}_{inc}"),
        InlineKeyboardButton(f"⬆️ +{inc*2:,}", callback_data=f"bid_{aid}_{inc*2}")
    )
    markup.row(
        InlineKeyboardButton(f"⬆️ +{inc*5:,}", callback_data=f"bid_{aid}_{inc*5}"),
        InlineKeyboardButton("✍️ مبلغ مخصص", callback_data=f"custombid_{aid}")
    )
    return markup

# --- /start ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name or "مجهول"
    database.ensure_user(uid, uname)
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📋 المزادات الحالية", callback_data="list_auctions"))
    
    # إضافة أزرار الإدارة للمشرفين
    if uid == OWNER_ID:
        markup.row(InlineKeyboardButton("👑 لوحة المالك", callback_data="owner_panel"))
        markup.row(InlineKeyboardButton("➕ إنشاء مزاد جديد", callback_data="create_auction"))
    elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("⚙️ لوحة المشرف", callback_data="admin_panel"))
    
    bot.send_message(uid,
        "🏷️ **مرحباً بك في بوت المزادات!**\n\n"
        "هنا تقدر تشارك في مزادات حية وتنافس على أفضل السلع.\n"
        "اختر من القائمة أدناه:",
        reply_markup=markup, parse_mode="Markdown")

# --- Owner Panel ---
@bot.callback_query_handler(func=lambda c: c.data == "owner_panel")
def owner_panel(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⛔ هذه اللوحة للمالك فقط!", show_alert=True)
        return
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin"))
    markup.row(InlineKeyboardButton("❌ طرد مشرف", callback_data="remove_admin"))
    markup.row(InlineKeyboardButton("➕ إنشاء مزاد جديد", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="go_home"))
    
    bot.edit_message_text(
        "👑 **لوحة تحكم المالك**\n\n"
        "من هنا تقدر تدير البوت بالكامل:",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Admin Panel ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
    if not database.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية!", show_alert=True)
        return
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ إنشاء مزاد جديد", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="go_home"))
    
    bot.edit_message_text(
        "⚙️ **لوحة المشرف**\n\nمن هنا تقدر تنشئ مزادات جديدة:",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Go Home ---
@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📋 المزادات الحالية", callback_data="list_auctions"))
    if uid == OWNER_ID:
        markup.row(InlineKeyboardButton("👑 لوحة المالك", callback_data="owner_panel"))
        markup.row(InlineKeyboardButton("➕ إنشاء مزاد جديد", callback_data="create_auction"))
    elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("⚙️ لوحة المشرف", callback_data="admin_panel"))
    
    bot.edit_message_text(
        "🏷️ **بوت المزادات**\nاختر من القائمة:",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Add Admin ---
@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_handler(call):
    if call.from_user.id != OWNER_ID:
        return
    user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("👮 أرسل لي الآي دي (ID) الرقمي للمشرف الجديد:", 
                          call.message.chat.id, call.message.message_id)

# --- Remove Admin ---
@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_handler(call):
    if call.from_user.id != OWNER_ID:
        return
    user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("🚫 أرسل لي الآي دي (ID) الرقمي للمشرف المراد طرده:",
                          call.message.chat.id, call.message.message_id)

# --- Create Auction Flow ---
@bot.callback_query_handler(func=lambda c: c.data == "create_auction")
def create_auction_handler(call):
    uid = call.from_user.id
    if not database.is_admin(uid):
        bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية!", show_alert=True)
        return
    user_states[uid] = "AUC_TITLE"
    admin_auction_data[uid] = {}
    bot.edit_message_text("📦 **إنشاء مزاد جديد**\n\n✏️ الخطوة 1/6: أرسل **اسم السلعة**:",
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- List Active Auctions ---
@bot.callback_query_handler(func=lambda c: c.data == "list_auctions")
def list_auctions_handler(call):
    auctions = database.get_active_auctions()
    if not auctions:
        bot.answer_callback_query(call.id, "📭 لا يوجد مزادات حالياً!", show_alert=True)
        return
    
    # Show first auction
    for auc in auctions:
        text = build_auction_text(auc)
        markup = build_bid_buttons(auc)
        
        # Add end auction button for admins
        if database.is_admin(call.from_user.id):
            markup.row(InlineKeyboardButton("🔴 إنهاء المزاد", callback_data=f"end_{auc['id']}"))
        
        if auc.get('photo_id'):
            bot.send_photo(call.message.chat.id, auc['photo_id'], caption=text, 
                          reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- Bidding Logic ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
    uid = call.from_user.id
    uname = call.from_user.username or call.from_user.first_name or "مجهول"
    database.ensure_user(uid, uname)
    
    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "⛔ هذا المزاد منتهي!", show_alert=True)
        return
    
    # Check if same person is highest bidder
    if auction['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "⚠️ أنت بالفعل صاحب أعلى سومة!", show_alert=True)
        return
    
    # Check pledge
    if not database.has_pledged(uid):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ أوافق وأتعهد", callback_data=f"pledge_{auction_id}_{bid_amount}"))
        markup.row(InlineKeyboardButton("❌ إلغاء", callback_data="go_home"))
        bot.send_message(uid,
            "⚖️ **تعهد المزايدة**\n\n"
            "قبل المزايدة، يجب عليك الموافقة على التعهد التالي:\n\n"
            "📜 *أتعهد أمام الله بالالتزام بدفع المبلغ في حال رسى المزاد علي، "
            "وأن لا أتراجع عن المزايدة بعد تأكيدها.*\n\n"
            "هل توافق؟",
            reply_markup=markup, parse_mode="Markdown")
        return
    
    new_price = auction['current_price'] + bid_amount
    
    # Confirmation
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تأكيد المزايدة", callback_data=f"confirm_{auction_id}_{new_price}"),
        InlineKeyboardButton("❌ إلغاء", callback_data=f"cancelbid")
    )
    c = cur(auction['currency'])
    bot.answer_callback_query(call.id)
    bot.send_message(uid,
        f"❓ **تأكيد المزايدة**\n\n"
        f"السعر الحالي: {auction['current_price']:,} {c}\n"
        f"مبلغ الزيادة: +{bid_amount:,} {c}\n"
        f"سومتك الجديدة: **{new_price:,} {c}**\n\n"
        f"هل أنت متأكد؟",
        reply_markup=markup, parse_mode="Markdown")

# --- Pledge Accept ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("pledge_"))
def handle_pledge(call):
    uid = call.from_user.id
    database.set_pledged(uid)
    
    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "⛔ المزاد انتهى!", show_alert=True)
        return
    
    new_price = auction['current_price'] + bid_amount
    c = cur(auction['currency'])
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تأكيد المزايدة", callback_data=f"confirm_{auction_id}_{new_price}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancelbid")
    )
    bot.edit_message_text(
        f"✅ تم قبول التعهد!\n\n"
        f"❓ **تأكيد المزايدة**\n"
        f"سومتك: **{new_price:,} {c}**\n\nهل أنت متأكد؟",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Confirm Bid ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm_bid(call):
    uid = call.from_user.id
    parts = call.data.split("_")
    auction_id = int(parts[1])
    new_price = int(parts[2])
    
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "⛔ المزاد انتهى!", show_alert=True)
        return
    
    if new_price <= auction['current_price']:
        bot.answer_callback_query(call.id, "⚠️ شخص سبقك! السعر ارتفع، حاول مرة أخرى.", show_alert=True)
        return
    
    if auction['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "⚠️ أنت بالفعل صاحب أعلى سومة!", show_alert=True)
        return
    
    database.place_bid(auction_id, uid, new_price)
    
    c = cur(auction['currency'])
    bot.edit_message_text(
        f"🎉 **تمت المزايدة بنجاح!**\n\nسومتك: **{new_price:,} {c}** على المزاد #{auction_id}",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    # Update auction message for everyone who has it
    updated_auction = database.get_auction(auction_id)
    # Notify in the chat
    uname = call.from_user.username or call.from_user.first_name or "مجهول"
    if len(uname) > 3:
        uname = uname[:3] + "***"
    
    bot.send_message(call.message.chat.id,
        f"🔔 **تحديث المزاد #{auction_id}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 سومة جديدة: **{new_price:,} {c}**\n"
        f"👤 من: {uname}",
        parse_mode="Markdown")

# --- Custom Bid ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_handler(call):
    uid = call.from_user.id
    auction_id = int(call.data.split("_")[1])
    
    if not database.has_pledged(uid):
        database.ensure_user(uid, call.from_user.username or call.from_user.first_name or "مجهول")
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ أوافق وأتعهد", callback_data=f"pledgecustom_{auction_id}"))
        markup.row(InlineKeyboardButton("❌ إلغاء", callback_data="go_home"))
        bot.send_message(uid,
            "⚖️ **تعهد المزايدة**\n\n"
            "📜 *أتعهد أمام الله بالالتزام بدفع المبلغ في حال رسى المزاد علي.*\n\nهل توافق؟",
            reply_markup=markup, parse_mode="Markdown")
        return
    
    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.answer_callback_query(call.id)
    bot.send_message(uid,
        f"✍️ اكتب المبلغ الإجمالي الذي تريد المزايدة به:\n"
        f"(يجب أن يكون أعلى من {auction['current_price'] + auction['min_increment']:,} {c})")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledgecustom_"))
def pledge_custom(call):
    uid = call.from_user.id
    database.set_pledged(uid)
    auction_id = int(call.data.split("_")[1])
    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.edit_message_text(
        f"✅ تم قبول التعهد!\n\n✍️ اكتب المبلغ الإجمالي:\n"
        f"(أعلى من {auction['current_price'] + auction['min_increment']:,} {c})",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- Cancel bid ---
@bot.callback_query_handler(func=lambda c: c.data == "cancelbid")
def cancel_bid(call):
    bot.edit_message_text("❌ تم إلغاء المزايدة.", call.message.chat.id, call.message.message_id)

# --- End Auction ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auction_handler(call):
    if not database.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ ليس لديك صلاحية!", show_alert=True)
        return
    
    auction_id = int(call.data.split("_")[1])
    auction = database.get_auction(auction_id)
    if not auction:
        return
    
    database.end_auction(auction_id)
    c = cur(auction['currency'])
    
    winner = "لا يوجد فائز (لم يزايد أحد)"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
        winner = database.get_username(auction['highest_bidder'])
    
    bot.send_message(call.message.chat.id,
        f"🏆 **انتهى المزاد #{auction_id}!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 السلعة: {auction['title']}\n"
        f"💰 السعر النهائي: **{auction['current_price']:,} {c}**\n"
        f"🥇 الفائز: **@{winner}**\n\n"
        f"📞 يرجى التواصل مع المالك لإتمام الصفقة.",
        parse_mode="Markdown")
    bot.answer_callback_query(call.id, "✅ تم إنهاء المزاد!")

# --- Text Handler (FSM) ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
    uid = message.from_user.id
    state = user_states.get(uid, "IDLE")
    
    # --- Owner: Add/Remove Admin ---
    if state == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
        try:
            new_admin_id = int(message.text.strip())
            database.add_admin(new_admin_id)
            bot.send_message(uid, f"✅ تم إضافة المشرف: `{new_admin_id}`", parse_mode="Markdown")
        except:
            bot.send_message(uid, "❌ أرسل رقم ID صحيح!")
        user_states[uid] = "IDLE"
        return
    
    if state == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
        try:
            rem_id = int(message.text.strip())
            database.remove_admin(rem_id)
            bot.send_message(uid, f"✅ تم طرد المشرف: `{rem_id}`", parse_mode="Markdown")
        except:
            bot.send_message(uid, "❌ أرسل رقم ID صحيح!")
        user_states[uid] = "IDLE"
        return
    
    # --- Auction Creation FSM ---
    if state == "AUC_TITLE" and database.is_admin(uid):
        admin_auction_data[uid] = {"title": message.text.strip()}
        user_states[uid] = "AUC_DESC"
        bot.send_message(uid, "📝 الخطوة 2/6: أرسل **وصف السلعة** (أو اكتب `-` لتخطي):", parse_mode="Markdown")
        return
    
    if state == "AUC_DESC" and database.is_admin(uid):
        desc = message.text.strip()
        admin_auction_data[uid]["description"] = "" if desc == "-" else desc
        user_states[uid] = "AUC_CURRENCY"
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🇸🇦 ريال سعودي", callback_data="cur_SAR"),
            InlineKeyboardButton("🇺🇸 دولار أمريكي", callback_data="cur_USD")
        )
        bot.send_message(uid, "💱 الخطوة 3/6: اختر **عملة المزاد**:", reply_markup=markup, parse_mode="Markdown")
        return
    
    if state == "AUC_START_PRICE" and database.is_admin(uid):
        try:
            price = int(message.text.strip())
            admin_auction_data[uid]["start_price"] = price
            user_states[uid] = "AUC_INCREMENT"
            bot.send_message(uid, "📈 الخطوة 5/6: أرسل **أقل مبلغ زيادة مسموح** (مثال: 10 أو 50):", parse_mode="Markdown")
        except:
            bot.send_message(uid, "❌ أرسل رقماً صحيحاً!")
        return
    
    if state == "AUC_INCREMENT" and database.is_admin(uid):
        try:
            inc = int(message.text.strip())
            admin_auction_data[uid]["min_increment"] = inc
            user_states[uid] = "AUC_PHOTO"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("⏭️ تخطي بدون صورة", callback_data="skip_photo"))
            bot.send_message(uid, "📸 الخطوة 6/6: أرسل **صورة السلعة** أو اضغط تخطي:", 
                           reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(uid, "❌ أرسل رقماً صحيحاً!")
        return
    
    if state == "AUC_PHOTO" and database.is_admin(uid):
        if message.photo:
            photo_id = message.photo[-1].file_id
            admin_auction_data[uid]["photo_id"] = photo_id
            _publish_auction(uid)
        else:
            bot.send_message(uid, "❌ أرسل صورة أو اضغط تخطي!")
        return
    
    # --- Custom Bid ---
    if state.startswith("CUSTOM_BID_"):
        auction_id = int(state.split("_")[2])
        auction = database.get_auction(auction_id)
        if not auction or auction['status'] != 'active':
            bot.send_message(uid, "⛔ المزاد منتهي!")
            user_states[uid] = "IDLE"
            return
        try:
            amount = int(message.text.strip())
            min_required = auction['current_price'] + auction['min_increment']
            if amount < min_required:
                c = cur(auction['currency'])
                bot.send_message(uid, f"⚠️ يجب أن يكون المبلغ أعلى من {min_required:,} {c}")
                return
            if auction['highest_bidder'] == uid:
                bot.send_message(uid, "⚠️ أنت بالفعل صاحب أعلى سومة!")
                user_states[uid] = "IDLE"
                return
            
            c = cur(auction['currency'])
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{auction_id}_{amount}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancelbid")
            )
            bot.send_message(uid,
                f"❓ تأكيد المزايدة بمبلغ **{amount:,} {c}**؟",
                reply_markup=markup, parse_mode="Markdown")
            user_states[uid] = "IDLE"
        except:
            bot.send_message(uid, "❌ أرسل رقماً صحيحاً فقط!")
        return

# --- Currency Selection Callback ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def currency_select(call):
    uid = call.from_user.id
    currency = call.data.split("_")[1]
    admin_auction_data[uid]["currency"] = currency
    user_states[uid] = "AUC_START_PRICE"
    c = cur(currency)
    bot.edit_message_text(f"💰 الخطوة 4/6: أرسل **سعر بداية المزاد** بالـ{c}:", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- Skip Photo ---
@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
    uid = call.from_user.id
    admin_auction_data[uid]["photo_id"] = None
    _publish_auction(uid)

# --- Publish Auction ---
def _publish_auction(uid):
    data = admin_auction_data.get(uid, {})
    auction_id = database.create_auction(
        data.get("title", "بدون عنوان"),
        data.get("description", ""),
        data.get("photo_id"),
        data.get("currency", "SAR"),
        data.get("start_price", 100),
        data.get("min_increment", 10)
    )
    
    auction = database.get_auction(auction_id)
    text = build_auction_text(auction)
    markup = build_bid_buttons(auction)
    markup.row(InlineKeyboardButton("🔴 إنهاء المزاد", callback_data=f"end_{auction_id}"))
    
    if data.get("photo_id"):
        bot.send_photo(uid, data["photo_id"], caption=text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")
    
    bot.send_message(uid, f"✅ تم نشر المزاد #{auction_id} بنجاح!")
    user_states[uid] = "IDLE"
    admin_auction_data.pop(uid, None)

# --- Run ---
print("✅ بوت المزادات يعمل الآن...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Error: {e}")
