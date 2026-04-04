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
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- Bot Setup ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)

database.init_db()
database.set_config("owner_id", str(OWNER_ID))

# --- State Machine ---
user_states = {}
admin_auction_data = {}

# --- Helpers ---
def cur(currency):
    return "\u0631\u064a\u0627\u0644" if currency == "SAR" else "$"

def is_private(message):
    return message.chat.type == "private"

def build_auction_text(auction):
    c = cur(auction['currency'])
    bidder_name = "\u0644\u0627 \u064a\u0648\u062c\u062f \u0628\u0639\u062f"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
        bidder_name = database.get_username(auction['highest_bidder'])
        if len(bidder_name) > 3:
            bidder_name = bidder_name[:3] + "***"

    if auction['status'] == 'active':
        status_line = "\U0001f7e2 \u062c\u0627\u0631\u064a"
    else:
        status_line = "\U0001f534 \u0645\u0646\u062a\u0647\u064a"

    text = f"\U0001f3f7\ufe0f *\u0645\u0632\u0627\u062f \u0631\u0642\u0645 #{auction['id']}*\n"
    text += "\u2501" * 18 + "\n"
    text += f"\U0001f4e6 *\u0627\u0644\u0633\u0644\u0639\u0629:* {auction['title']}\n"
    if auction.get('description'):
        text += f"\U0001f4dd *\u0627\u0644\u0648\u0635\u0641:* {auction['description']}\n"
    text += "\u2501" * 18 + "\n"
    text += f"\U0001f4b0 *\u0633\u0639\u0631 \u0627\u0644\u0627\u0641\u062a\u062a\u0627\u062d:* {auction['start_price']:,} {c}\n"
    text += f"\U0001f4c8 *\u0623\u0642\u0644 \u0632\u064a\u0627\u062f\u0629:* {auction['min_increment']:,} {c}\n"
    text += "\u2501" * 18 + "\n"
    text += f"\U0001f525 *\u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629:* {auction['current_price']:,} {c}\n"
    text += f"\U0001f464 *\u0635\u0627\u062d\u0628\u0647\u0627:* {bidder_name}\n"
    text += f"\U0001f4ca *\u0627\u0644\u062d\u0627\u0644\u0629:* {status_line}\n"
    text += "\u2501" * 18 + "\n"
    text += "\u26a0\ufe0f _\u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629 \u062a\u0639\u0646\u064a \u0627\u0644\u062a\u0632\u0627\u0645 \u0628\u0627\u0644\u062f\u0641\u0639_"
    return text

def build_bid_buttons(auction):
    markup = InlineKeyboardMarkup()
    if auction['status'] != 'active':
        return markup
    inc = auction['min_increment']
    aid = auction['id']
    markup.row(
        InlineKeyboardButton(f"\u2b06\ufe0f +{inc:,}", callback_data=f"bid_{aid}_{inc}"),
        InlineKeyboardButton(f"\u2b06\ufe0f +{inc*2:,}", callback_data=f"bid_{aid}_{inc*2}")
    )
    markup.row(
        InlineKeyboardButton(f"\u2b06\ufe0f +{inc*5:,}", callback_data=f"bid_{aid}_{inc*5}"),
        InlineKeyboardButton(f"\u2b06\ufe0f +{inc*10:,}", callback_data=f"bid_{aid}_{inc*10}")
    )
    markup.row(
        InlineKeyboardButton("\u270d\ufe0f \u0645\u0628\u0644\u063a \u0645\u062e\u0635\u0635", callback_data=f"custombid_{aid}")
    )
    return markup

def refresh_auction_in_group(auction_id):
    """Update the auction message in the group"""
    auction = database.get_auction(auction_id)
    if not auction:
        return
    msg_id = auction.get('group_message_id')
    if not msg_id or not GROUP_ID:
        return
    text = build_auction_text(auction)
    markup = build_bid_buttons(auction)
    try:
        if auction.get('photo_id'):
            bot.edit_message_caption(
                caption=text, chat_id=GROUP_ID, message_id=msg_id,
                reply_markup=markup, parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                text, GROUP_ID, msg_id,
                reply_markup=markup, parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Error updating group message: {e}")

# ===== PRIVATE CHAT COMMANDS =====

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_private(message):
        return
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name or "\u0645\u0633\u062a\u062e\u062f\u0645"
    database.ensure_user(uid, uname)

    markup = InlineKeyboardMarkup()
    if uid == OWNER_ID:
        markup.row(InlineKeyboardButton("\U0001f451 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
        markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
        markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    else:
        markup.row(InlineKeyboardButton("\U0001f4cb \u0645\u0632\u0627\u062f\u0627\u062a\u064a", callback_data="my_bids"))

    bot.send_message(uid,
        "\U0001f3f7\ufe0f *\u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643 \u0641\u064a \u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a!*\n\n"
        "\U0001f4e2 \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u062a\u0646\u0632\u0644 \u0641\u064a \u0627\u0644\u0642\u0631\u0648\u0628 \u0645\u0628\u0627\u0634\u0631\u0629\n"
        "\u2705 \u0632\u0627\u064a\u062f \u0645\u0646 \u0627\u0644\u0642\u0631\u0648\u0628 \u0628\u0636\u063a\u0637\u0629 \u0632\u0631\n\n"
        "\u0627\u062e\u062a\u0631 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629:",
        reply_markup=markup, parse_mode="Markdown")

# --- Owner Panel ---
@bot.callback_query_handler(func=lambda c: c.data == "owner_panel")
def owner_panel(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "\u26d4", show_alert=True)
        return
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0636\u0627\u0641\u0629 \u0645\u0634\u0631\u0641", callback_data="add_admin"))
    markup.row(InlineKeyboardButton("\u274c \u0637\u0631\u062f \u0645\u0634\u0631\u0641", callback_data="remove_admin"))
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("\U0001f6d1 \u0625\u0646\u0647\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="end_auction_select"))
    markup.row(InlineKeyboardButton("\U0001f519 \u0631\u062c\u0648\u0639", callback_data="go_home"))
    bot.edit_message_text(
        "\U0001f451 *\u0644\u0648\u062d\u0629 \u062a\u062d\u0643\u0645 \u0627\u0644\u0645\u0627\u0644\u0643*\n\n\u0645\u0646 \u0647\u0646\u0627 \u062a\u062f\u064a\u0631 \u0643\u0644 \u0634\u064a\u0621:",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Admin Panel ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
    if not database.is_admin(call.from_user.id):
        return
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("\U0001f6d1 \u0625\u0646\u0647\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="end_auction_select"))
    markup.row(InlineKeyboardButton("\U0001f519 \u0631\u062c\u0648\u0639", callback_data="go_home"))
    bot.edit_message_text(
        "\u2699\ufe0f *\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641*",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Go Home ---
@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    if uid == OWNER_ID:
        markup.row(InlineKeyboardButton("\U0001f451 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
    elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
    bot.edit_message_text(
        "\U0001f3f7\ufe0f *\u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a*\n\u0627\u062e\u062a\u0631 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629:",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

# --- Add/Remove Admin ---
@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_h(call):
    if call.from_user.id != OWNER_ID:
        return
    user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("\U0001f46e \u0623\u0631\u0633\u0644 \u0622\u064a\u062f\u064a \u0627\u0644\u0645\u0634\u0631\u0641 \u0627\u0644\u062c\u062f\u064a\u062f:",
                          call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_h(call):
    if call.from_user.id != OWNER_ID:
        return
    user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("\U0001f6ab \u0623\u0631\u0633\u0644 \u0622\u064a\u062f\u064a \u0627\u0644\u0645\u0634\u0631\u0641 \u0627\u0644\u0645\u0631\u0627\u062f \u0637\u0631\u062f\u0647:",
                          call.message.chat.id, call.message.message_id)

# --- Create Auction ---
@bot.callback_query_handler(func=lambda c: c.data == "create_auction")
def create_auction_h(call):
    uid = call.from_user.id
    if not database.is_admin(uid):
        return
    if GROUP_ID == 0:
        bot.answer_callback_query(call.id, "\u26d4 \u0644\u0645 \u064a\u062a\u0645 \u062a\u0639\u064a\u064a\u0646 GROUP_ID!", show_alert=True)
        return
    user_states[uid] = "AUC_TITLE"
    admin_auction_data[uid] = {}
    bot.edit_message_text(
        "\U0001f4e6 *\u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f*\n\n"
        "\u270f\ufe0f \u0627\u0644\u062e\u0637\u0648\u0629 1/6: \u0623\u0631\u0633\u0644 *\u0627\u0633\u0645 \u0627\u0644\u0633\u0644\u0639\u0629*:",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- End Auction Select ---
@bot.callback_query_handler(func=lambda c: c.data == "end_auction_select")
def end_auction_select(call):
    if not database.is_admin(call.from_user.id):
        return
    auctions = database.get_active_auctions()
    if not auctions:
        bot.answer_callback_query(call.id, "\u0644\u0627 \u064a\u0648\u062c\u062f \u0645\u0632\u0627\u062f\u0627\u062a!", show_alert=True)
        return
    markup = InlineKeyboardMarkup()
    for a in auctions:
        markup.row(InlineKeyboardButton(
            f"#{a['id']} - {a['title']}", callback_data=f"end_{a['id']}"))
    markup.row(InlineKeyboardButton("\U0001f519 \u0631\u062c\u0648\u0639", callback_data="go_home"))
    bot.edit_message_text("\U0001f6d1 \u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u0632\u0627\u062f \u0644\u0625\u0646\u0647\u0627\u0626\u0647:",
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- My Bids ---
@bot.callback_query_handler(func=lambda c: c.data == "my_bids")
def my_bids(call):
    bot.answer_callback_query(call.id, "\u0642\u0631\u064a\u0628\u0627\u064b!", show_alert=True)

# ===== GROUP BIDDING =====

@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
    uid = call.from_user.id
    uname = call.from_user.username or call.from_user.first_name or "\u0645\u0633\u062a\u062e\u062f\u0645"
    database.ensure_user(uid, uname)

    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])

    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "\u26d4 \u0627\u0644\u0645\u0632\u0627\u062f \u0645\u0646\u062a\u0647\u064a!", show_alert=True)
        return

    if auction['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0623\u0646\u062a \u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629!", show_alert=True)
        return

    if not database.has_pledged(uid):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("\u2705 \u0623\u062a\u0639\u0647\u062f \u0648\u0623\u0648\u0627\u0641\u0642", callback_data=f"pledge_{auction_id}_{bid_amount}"))
        markup.row(InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid"))
        bot.send_message(uid,
            "\u2696\ufe0f *\u062a\u0639\u0647\u062f \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629*\n\n"
            "\U0001f4dc _\u0623\u062a\u0639\u0647\u062f \u0623\u0645\u0627\u0645 \u0627\u0644\u0644\u0647 \u0628\u0627\u0644\u0627\u0644\u062a\u0632\u0627\u0645 \u0628\u0627\u0644\u062f\u0641\u0639 \u0625\u0630\u0627 \u0631\u0633\u0649 \u0627\u0644\u0645\u0632\u0627\u062f \u0639\u0644\u064a._\n\n"
            "\u0647\u0644 \u062a\u0648\u0627\u0641\u0642\u061f",
            reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        return

    new_price = auction['current_price'] + bid_amount
    c = cur(auction['currency'])

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("\u2705 \u062a\u0623\u0643\u064a\u062f", callback_data=f"confirm_{auction_id}_{new_price}"),
        InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid")
    )
    bot.send_message(uid,
        f"\u2753 *\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629*\n\n"
        f"\u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u062d\u0627\u0644\u064a: {auction['current_price']:,} {c}\n"
        f"\u0627\u0644\u0632\u064a\u0627\u062f\u0629: +{bid_amount:,} {c}\n"
        f"\u0633\u0648\u0645\u062a\u0643: *{new_price:,} {c}*\n\n"
        f"\u0645\u062a\u0623\u0643\u062f\u061f",
        reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- Pledge ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("pledge_"))
def handle_pledge(call):
    uid = call.from_user.id
    database.set_pledged(uid)
    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "\u26d4 \u0627\u0646\u062a\u0647\u0649!", show_alert=True)
        return
    new_price = auction['current_price'] + bid_amount
    c = cur(auction['currency'])
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("\u2705 \u062a\u0623\u0643\u064a\u062f", callback_data=f"confirm_{auction_id}_{new_price}"),
        InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid")
    )
    bot.edit_message_text(
        f"\u2705 \u062a\u0645 \u0642\u0628\u0648\u0644 \u0627\u0644\u062a\u0639\u0647\u062f!\n\n"
        f"\u0633\u0648\u0645\u062a\u0643: *{new_price:,} {c}*\n\u0645\u062a\u0623\u0643\u062f\u061f",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledgecustom_"))
def pledge_custom(call):
    uid = call.from_user.id
    database.set_pledged(uid)
    auction_id = int(call.data.split("_")[1])
    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.edit_message_text(
        f"\u2705 \u062a\u0645 \u0642\u0628\u0648\u0644 \u0627\u0644\u062a\u0639\u0647\u062f!\n\n"
        f"\u270d\ufe0f \u0627\u0643\u062a\u0628 \u0627\u0644\u0645\u0628\u0644\u063a (\u0623\u0639\u0644\u0649 \u0645\u0646 {auction['current_price']+auction['min_increment']:,} {c}):",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- Confirm Bid ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm_bid(call):
    uid = call.from_user.id
    parts = call.data.split("_")
    auction_id = int(parts[1])
    new_price = int(parts[2])

    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
        bot.answer_callback_query(call.id, "\u26d4 \u0627\u0646\u062a\u0647\u0649!", show_alert=True)
        return
    if new_price <= auction['current_price']:
        bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0634\u062e\u0635 \u0633\u0628\u0642\u0643!", show_alert=True)
        return
    if auction['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "\u0623\u0646\u062a \u0627\u0644\u0623\u0639\u0644\u0649!", show_alert=True)
        return

    # Notify previous highest bidder
    prev_bidder = auction['highest_bidder']

    database.place_bid(auction_id, uid, new_price)
    c = cur(auction['currency'])

    bot.edit_message_text(
        f"\U0001f389 *\u062a\u0645\u062a \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629!*\n\n"
        f"\u0633\u0648\u0645\u062a\u0643: *{new_price:,} {c}* \u0639\u0644\u0649 #{auction_id}",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    # Update group message
    refresh_auction_in_group(auction_id)

    # Notify previous bidder
    if prev_bidder and prev_bidder != 0 and prev_bidder != uid:
        try:
            bot.send_message(prev_bidder,
                f"\U0001f514 *\u062a\u0646\u0628\u064a\u0647!*\n\n"
                f"\u062a\u0645 \u0643\u0633\u0631 \u0633\u0648\u0645\u062a\u0643 \u0639\u0644\u0649 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}\n"
                f"\u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u062c\u062f\u064a\u062f: *{new_price:,} {c}*",
                parse_mode="Markdown")
        except:
            pass

# --- Custom Bid ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_h(call):
    uid = call.from_user.id
    auction_id = int(call.data.split("_")[1])

    if not database.has_pledged(uid):
        database.ensure_user(uid, call.from_user.username or call.from_user.first_name or "\u0645\u0633\u062a\u062e\u062f\u0645")
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("\u2705 \u0623\u062a\u0639\u0647\u062f", callback_data=f"pledgecustom_{auction_id}"))
        markup.row(InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid"))
        bot.send_message(uid,
            "\u2696\ufe0f *\u062a\u0639\u0647\u062f \u0645\u0637\u0644\u0648\u0628*\n\n\u0647\u0644 \u062a\u0648\u0627\u0641\u0642\u061f",
            reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        return

    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.send_message(uid,
        f"\u270d\ufe0f \u0627\u0643\u062a\u0628 \u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a:\n"
        f"(\u0623\u0639\u0644\u0649 \u0645\u0646 {auction['current_price']+auction['min_increment']:,} {c})")
    bot.answer_callback_query(call.id)

# --- Cancel ---
@bot.callback_query_handler(func=lambda c: c.data == "cancelbid")
def cancel_bid(call):
    bot.edit_message_text("\u274c \u062a\u0645 \u0627\u0644\u0625\u0644\u063a\u0627\u0621.", call.message.chat.id, call.message.message_id)

# --- End Auction ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auction_h(call):
    if not database.is_admin(call.from_user.id):
        return
    auction_id = int(call.data.split("_")[1])
    auction = database.get_auction(auction_id)
    if not auction:
        return

    database.end_auction(auction_id)
    c = cur(auction['currency'])

    winner = "\u0644\u0627 \u064a\u0648\u062c\u062f \u0641\u0627\u0626\u0632"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
        winner = database.get_username(auction['highest_bidder'])

    result_text = (
        f"\U0001f3c6 *\u0627\u0646\u062a\u0647\u0649 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}!*\n"
        f"\u2501" * 18 + "\n"
        f"\U0001f4e6 {auction['title']}\n"
        f"\U0001f4b0 \u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u0646\u0647\u0627\u0626\u064a: *{auction['current_price']:,} {c}*\n"
        f"\U0001f947 \u0627\u0644\u0641\u0627\u0626\u0632: *@{winner}*\n\n"
        f"\U0001f4de \u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0645\u0627\u0644\u0643 \u0644\u0625\u062a\u0645\u0627\u0645 \u0627\u0644\u0635\u0641\u0642\u0629."
    )

    # Post result in group
    if GROUP_ID:
        try:
            bot.send_message(GROUP_ID, result_text, parse_mode="Markdown")
        except:
            pass

    # Update group message to show ended
    refresh_auction_in_group(auction_id)

    # Notify winner privately
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
        try:
            bot.send_message(auction['highest_bidder'],
                f"\U0001f389 *\u0645\u0628\u0631\u0648\u0643!*\n\n"
                f"\u0631\u0633\u0649 \u0639\u0644\u064a\u0643 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}\n"
                f"\u0627\u0644\u0645\u0628\u0644\u063a: *{auction['current_price']:,} {c}*\n\n"
                f"\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0645\u0627\u0644\u0643 \u0644\u0625\u062a\u0645\u0627\u0645 \u0627\u0644\u0635\u0641\u0642\u0629.",
                parse_mode="Markdown")
        except:
            pass

    bot.answer_callback_query(call.id, "\u2705 \u062a\u0645 \u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f!")
    # Return to panel
    if call.from_user.id == OWNER_ID:
        owner_panel(call)
    else:
        admin_panel(call)

# --- Currency Select ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def currency_select(call):
    uid = call.from_user.id
    currency = call.data.split("_")[1]
    admin_auction_data[uid]["currency"] = currency
    user_states[uid] = "AUC_START_PRICE"
    c = cur(currency)
    bot.edit_message_text(
        f"\U0001f4b0 \u0627\u0644\u062e\u0637\u0648\u0629 4/6: \u0623\u0631\u0633\u0644 *\u0633\u0639\u0631 \u0627\u0644\u0628\u062f\u0627\u064a\u0629* \u0628\u0627\u0644\u0640{c}:",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- Skip Photo ---
@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
    uid = call.from_user.id
    admin_auction_data[uid]["photo_id"] = None
    _publish_auction(uid)

# ===== TEXT HANDLER (FSM) =====
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
    uid = message.from_user.id
    if not is_private(message):
        return
    state = user_states.get(uid, "IDLE")

    if state == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
        try:
            nid = int(message.text.strip())
            database.add_admin(nid)
            bot.send_message(uid, f"\u2705 \u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u0631\u0641: `{nid}`", parse_mode="Markdown")
        except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 \u0635\u062d\u064a\u062d!")
        user_states[uid] = "IDLE"
        return

    if state == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
        try:
            rid = int(message.text.strip())
            database.remove_admin(rid)
            bot.send_message(uid, f"\u2705 \u062a\u0645 \u0637\u0631\u062f \u0627\u0644\u0645\u0634\u0631\u0641: `{rid}`", parse_mode="Markdown")
        except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 \u0635\u062d\u064a\u062d!")
        user_states[uid] = "IDLE"
        return

    if state == "AUC_TITLE" and database.is_admin(uid):
        admin_auction_data[uid] = {"title": message.text.strip()}
        user_states[uid] = "AUC_DESC"
        bot.send_message(uid, "\U0001f4dd \u0627\u0644\u062e\u0637\u0648\u0629 2/6: \u0623\u0631\u0633\u0644 *\u0627\u0644\u0648\u0635\u0641* (\u0623\u0648 `-` \u0644\u0644\u062a\u062e\u0637\u064a):", parse_mode="Markdown")
        return

    if state == "AUC_DESC" and database.is_admin(uid):
        desc = message.text.strip()
        admin_auction_data[uid]["description"] = "" if desc == "-" else desc
        user_states[uid] = "AUC_CURRENCY"
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("\U0001f1f8\U0001f1e6 \u0631\u064a\u0627\u0644", callback_data="cur_SAR"),
            InlineKeyboardButton("\U0001f1fa\U0001f1f8 \u062f\u0648\u0644\u0627\u0631", callback_data="cur_USD")
        )
        bot.send_message(uid, "\U0001f4b1 \u0627\u0644\u062e\u0637\u0648\u0629 3/6: \u0627\u062e\u062a\u0631 *\u0627\u0644\u0639\u0645\u0644\u0629*:", reply_markup=markup, parse_mode="Markdown")
        return

    if state == "AUC_START_PRICE" and database.is_admin(uid):
        try:
            price = int(message.text.strip())
            admin_auction_data[uid]["start_price"] = price
            user_states[uid] = "AUC_INCREMENT"
            bot.send_message(uid, "\U0001f4c8 \u0627\u0644\u062e\u0637\u0648\u0629 5/6: \u0623\u0631\u0633\u0644 *\u0623\u0642\u0644 \u0632\u064a\u0627\u062f\u0629* (\u0645\u062b\u0627\u0644: 10):", parse_mode="Markdown")
        except:
            bot.send_message(uid, "\u274c \u0631\u0642\u0645 \u063a\u0644\u0637!")
        return

    if state == "AUC_INCREMENT" and database.is_admin(uid):
        try:
            inc = int(message.text.strip())
            admin_auction_data[uid]["min_increment"] = inc
            user_states[uid] = "AUC_PHOTO"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("\u23ed\ufe0f \u062a\u062e\u0637\u064a", callback_data="skip_photo"))
            bot.send_message(uid, "\U0001f4f8 \u0627\u0644\u062e\u0637\u0648\u0629 6/6: \u0623\u0631\u0633\u0644 *\u0635\u0648\u0631\u0629* \u0623\u0648 \u062a\u062e\u0637\u064a:", reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(uid, "\u274c \u0631\u0642\u0645 \u063a\u0644\u0637!")
        return

    if state == "AUC_PHOTO" and database.is_admin(uid):
        if message.photo:
            admin_auction_data[uid]["photo_id"] = message.photo[-1].file_id
            _publish_auction(uid)
        else:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0623\u0648 \u0627\u0636\u063a\u0637 \u062a\u062e\u0637\u064a!")
        return

    if state.startswith("CUSTOM_BID_"):
        auction_id = int(state.split("_")[2])
        auction = database.get_auction(auction_id)
        if not auction or auction['status'] != 'active':
            bot.send_message(uid, "\u26d4 \u0627\u0646\u062a\u0647\u0649!")
            user_states[uid] = "IDLE"
            return
        try:
            amount = int(message.text.strip())
            min_req = auction['current_price'] + auction['min_increment']
            if amount < min_req:
                c = cur(auction['currency'])
                bot.send_message(uid, f"\u26a0\ufe0f \u064a\u062c\u0628 \u0623\u0639\u0644\u0649 \u0645\u0646 {min_req:,} {c}")
                return
            if auction['highest_bidder'] == uid:
                bot.send_message(uid, "\u0623\u0646\u062a \u0627\u0644\u0623\u0639\u0644\u0649!")
                user_states[uid] = "IDLE"
                return
            c = cur(auction['currency'])
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("\u2705 \u062a\u0623\u0643\u064a\u062f", callback_data=f"confirm_{auction_id}_{amount}"),
                InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid")
            )
            bot.send_message(uid, f"\u062a\u0623\u0643\u064a\u062f \u0645\u0632\u0627\u064a\u062f\u0629 *{amount:,} {c}*\u061f", reply_markup=markup, parse_mode="Markdown")
            user_states[uid] = "IDLE"
        except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0642\u0627\u0645 \u0641\u0642\u0637!")
        return

# --- Publish Auction to Group ---
def _publish_auction(uid):
    data = admin_auction_data.get(uid, {})
    auction_id = database.create_auction(
        data.get("title", "\u0628\u062f\u0648\u0646 \u0639\u0646\u0648\u0627\u0646"),
        data.get("description", ""),
        data.get("photo_id"),
        data.get("currency", "SAR"),
        data.get("start_price", 100),
        data.get("min_increment", 10)
    )

    auction = database.get_auction(auction_id)
    text = build_auction_text(auction)
    markup = build_bid_buttons(auction)

    # Send to GROUP
    try:
        if data.get("photo_id"):
            sent = bot.send_photo(GROUP_ID, data["photo_id"], caption=text,
                                  reply_markup=markup, parse_mode="Markdown")
        else:
            sent = bot.send_message(GROUP_ID, text, reply_markup=markup, parse_mode="Markdown")
        # Save group message ID for later updates
        database.set_auction_group_msg(auction_id, sent.message_id)
    except Exception as e:
        bot.send_message(uid, f"\u274c \u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0625\u0631\u0633\u0627\u0644 \u0644\u0644\u0642\u0631\u0648\u0628: {e}")
        user_states[uid] = "IDLE"
        admin_auction_data.pop(uid, None)
        return

    bot.send_message(uid, f"\u2705 \u062a\u0645 \u0646\u0634\u0631 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id} \u0641\u064a \u0627\u0644\u0642\u0631\u0648\u0628!")
    user_states[uid] = "IDLE"
    admin_auction_data.pop(uid, None)

# --- Run ---
print("\u2705 \u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u064a\u0639\u0645\u0644...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Error: {e}")
