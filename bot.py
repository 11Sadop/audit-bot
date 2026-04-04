import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
import database

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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)
database.set_config("owner_id", str(OWNER_ID))

user_states = {}
admin_auction_data = {}

def cur(currency):
          return "def cur(currency):
    return "\u0631\u064a\u0627\u0644" if currency == "SAR" else "$"

def build_auction_text(auction):
          c = cur(auction['currency'])
    bidder_name = "\u0644\u0627 \u064a\u0648\u062c\u062f \u0628\u0639\u062f"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
                  bidder_name = database.get_username(auction['highest_bidder'])
                  if len(bidder_name) > 3:
                                    bidder_name = bidder_name[:3] + "***"
                            status_emoji = "\ud83d\udfe2 \u062c\u0627\u0631\u064a" if auction['status'] == 'active' else "\ud83d\udd34 \u0645\u0646\u062a\u0647\u064a"
    text = f"\ud83c\udff7\ufe0f **\u0645\u0632\u0627\u062f \u0631\u0642\u0645 #{auction['id']}**\n"
    text += f"----------------------------------\n"
    text += f"\ud83d\udce6 **\u0627\u0644\u0633\u0644\u0639\u0629:** {auction['title']}\n"
    if auction.get('description'):
                  text += f"\ud83d\udcdd **\u0648\u0635\u0641:** {auction['description']}\n"
    text += f"\ud83d\udcb0 **\u0633\u0639\u0631 \u0627\u0644\u0627\u0641\u062a\u062a\u0627\u062d:** {auction['start_price']:,} {c}\n"
    text += f"\ud83d\udcc8 **\u0623\u0642\u0644 \u0632\u064a\u0627\u062f\u0629:** {auction['min_increment']:,} {c}\n"
    text += f"----------------------------------\n"
    text += f"\ud83d\udd25 **\u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629 \u062d\u0627\u0644\u064a\u0627\u064b:** {auction['current_price']:,} {c}\n"
    text += f"\ud83d\udc64 **\u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629:** {bidder_name}\n"
    text += f"\ud83d\udcca **\u0627\u0644\u062d\u0627\u0644\u0629:** {status_emoji}\n"
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
                  InlineKeyboardButton("\u270d\ufe0f \u0645\u0628\u0644\u063a \u0645\u062e\u0635\u0635", callback_data=f"custombid_{aid}")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
          uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name or "\u0645\u062c\u0647\u0648\u0644"
    database.ensure_user(uid, uname)
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\ud83d\udccb \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u0627\u0644\u062d\u0627\u0644\u064a\u0629", callback_data="list_auctions"))
    if uid == OWNER_ID:
                  markup.row(InlineKeyboardButton("\ud83d\udc51 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
        markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="create_auction"))
elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
    bot.send_message(uid, "\ud83c\udff7\ufe0f **\u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643 \u0641\u064a \u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a!**\n\n\u0647\u0646\u0627 \u062a\u0642\u062f\u0631 \u062a\u0634\u0627\u0631\u0643 \u0641\u064a \u0645\u0632\u0627\u062f\u0627\u062a \u062d\u064a\u0629 \u0648\u062a\u0646\u0627\u0641\u0633 \u0639\u0644\u0649 \u0623\u0641\u0636\u0644 \u0627\u0644\u0633\u0644\u0639.\n\u0627\u062e\u062a\u0631 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u062f\u0646\u0627\u0647:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "owner_panel")
def owner_panel(call):
          if call.from_user.id != OWNER_ID:
                        bot.answer_callback_query(call.id, "\u26d4 \u0647\u0630\u0647 \u0627\u0644\u0644\u0648\u062d\u0629 \u0644\u0644\u0645\u0627\u0644\u0643 \u0641\u0642\u0637!", show_alert=True)
                        return
                    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0636\u0627\u0641\u0629 \u0645\u0634\u0631\u0641", callback_data="add_admin"))
    markup.row(InlineKeyboardButton("\u274c \u0637\u0631\u062f \u0645\u0634\u0631\u0641", callback_data="remove_admin"))
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("\ud83d\udd19 \u0631\u062c\u0648\u0639", callback_data="go_home"))
    bot.edit_message_text("\ud83d\udc51 **\u0644\u0648\u062d\u0629 \u062a\u062d\u0643\u0645 \u0627\u0644\u0645\u0627\u0644\u0643**\n\n\u0645\u0646 \u0647\u0646\u0627 \u062a\u0642\u062f\u0631 \u062a\u062f\u064a\u0631 \u0627\u0644\u0628\u0648\u062a \u0628\u0627\u0644\u0643\u0627\u0645\u0644:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
          if not database.is_admin(call.from_user.id):
                        bot.answer_callback_query(call.id, "\u26d4 \u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0635\u0644\u0627\u062d\u064a\u0629!", show_alert=True)
                        return
                    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="create_auction"))
    markup.row(InlineKeyboardButton("\ud83d\udd19 \u0631\u062c\u0648\u0639", callback_data="go_home"))
    bot.edit_message_text("\u2699\ufe0f **\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641**\n\n\u0645\u0646 \u0647\u0646\u0627 \u062a\u0642\u062f\u0631 \u062a\u0646\u0634\u0626 \u0645\u0632\u0627\u062f\u0627\u062a \u062c\u062f\u064a\u062f\u0629:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
          uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\ud83d\udccb \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u0627\u0644\u062d\u0627\u0644\u064a\u0629", callback_data="list_auctions"))
    if uid == OWNER_ID:
                  markup.row(InlineKeyboardButton("\ud83d\udc51 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
        markup.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="create_auction"))
elif database.is_admin(uid):
        markup.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
    bot.edit_message_text("\ud83c\udff7\ufe0f **\u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a**\n\u0627\u062e\u062a\u0631 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_handler(call):
          if call.from_user.id != OWNER_ID: return
                    user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("\ud83d\udc6e \u0623\u0631\u0633\u0644 \u0644\u064a \u0627\u0644\u0622\u064a \u062f\u064a (ID) \u0627\u0644\u0631\u0642\u0645\u064a \u0644\u0644\u0645\u0634\u0631\u0641 \u0627\u0644\u062c\u062f\u064a\u062f:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_handler(call):
          if call.from_user.id != OWNER_ID: return
                    user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("\ud83d\udeab \u0623\u0631\u0633\u0644 \u0644\u064a \u0627\u0644\u0622\u064a \u062f\u064a (ID) \u0627\u0644\u0631\u0642\u0645\u064a \u0644\u0644\u0645\u0634\u0631\u0641 \u0627\u0644\u0645\u0631\u0627\u062f \u0637\u0631\u062f\u0647:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "create_auction")
def create_auction_handler(call):
          uid = call.from_user.id
    if not database.is_admin(uid):
                  bot.answer_callback_query(call.id, "\u26d4 \u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0635\u0644\u0627\u062d\u064a\u0629!", show_alert=True)
        return
    user_states[uid] = "AUC_TITLE"
    admin_auction_data[uid] = {}
    bot.edit_message_text("\ud83d\udce6 **\u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f**\n\n\u270f\ufe0f \u0627\u0644\u062e\u0637\u0648\u0629 1/6: \u0623\u0631\u0633\u0644 **\u0627\u0633\u0645 \u0627\u0644\u0633\u0644\u0639\u0629**:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "list_auctions")
def list_auctions_handler(call):
          auctions = database.get_active_auctions()
    if not auctions:
                  bot.answer_callback_query(call.id, "\ud83d\udceb \u0644\u0627 \u064a\u0648\u062c\u062f \u0645\u0632\u0627\u062f\u0627\u062a \u062d\u0627\u0644\u064a\u0627\u064b!", show_alert=True)
        return
    for auc in auctions:
                  text = build_auction_text(auc)
        markup = build_bid_buttons(auc)
        if database.is_admin(call.from_user.id):
                          markup.row(InlineKeyboardButton("\ud83d\udd34 \u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f", callback_data=f"end_{auc['id']}"))
                      if auc.get('photo_id'):
                                        bot.send_photo(call.message.chat.id, auc['photo_id'], caption=text, reply_markup=markup, parse_mode="Markdown")
else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
          uid = call.from_user.id
    uname = call.from_user.username or call.from_user.first_name or "\u0645\u062c\u0647\u0648\u0644"
    database.ensure_user(uid, uname)
    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
                  bot.answer_callback_query(call.id, "\u26d4 \u0647\u0630\u0627 \u0627\u0644\u0645\u0632\u0627\u062f \u0645\u0646\u062a\u0647\u064a!", show_alert=True)
        return
    if auction['highest_bidder'] == uid:
                  bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0623\u0646\u062a \u0628\u0627\u0644\u0641\u0639\u0644 \u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629!", show_alert=True)
        return
    if not database.has_pledged(uid):
                  markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("\u2705 \u0623\u0648\u0627\u0641\u0642 \u0648\u0623\u062a\u0639\u0647\u062f", callback_data=f"pledge_{auction_id}_{bid_amount}"))
        markup.row(InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="go_home"))
        bot.send_message(uid, "\u2696\ufe0f **\u062a\u0639\u0647\u062f \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629**\n\n\u0642\u0628\u0644 \u0627\u0644\u0645\u0632\u0627\u062a \u061f \u064a\u062c\u0628 \u0639\u0644\u064a\u0643 \u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0629 \u0639\u0644\u0649 \u0627\u0644\u062a\u0639\u0647\u062f \u0627\u0644\u062a\u0627\u0644\u064a:\n\n\ud83d\udcdc *\u0623\u062a\u0639\u0647\u062f \u0623\u0645\u0627\u0645 \u0627\u0644\u0644\u0647 \u0628\u0627\u0644\u0627\u0644\u062a\u0632\u0627\u0645 \u0628\u062f\u0641\u0639 \u0627\u0644\u0645\u0628\u0644\u063a \u0641\u064a \u062d\u0627\u0644 \u0631\u0633\u0649 \u0627\u0644\u0645\u0632\u0627\u062f \u0639\u0644\u064a\u060b \u0648\u0623\u0646 \u0644\u0627 \u0623\u062a\u0631\u0627\u062c\u0639 \u0639\u0646 \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629 \u0628\u0639\u062f \u062a\u0623\u0643\u064a\u062f\u0647\u0627.*\n\n\u0647\u0644 \u062a\u0648\u0627\u0641\u0642\u061f", reply_markup=markup, parse_mode="Markdown")
        return

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledge_"))
def handle_pledge(call):
          uid = call.from_user.id
    database.set_pledged(uid)
    parts = call.data.split("_")
    auction_id = int(parts[1])
    bid_amount = int(parts[2])
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
                  bot.answer_callback_query(call.id, "\u26d4 \u0627\u0644\u0645\u0632\u0627\u062f \u0627\u0646\u062a\u0647\u0649!", show_alert=True)
        return
    new_price = auction['current_price'] + bid_amount
    c = cur(auction['currency'])
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("\u2705 \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u062a \u061f !", callback_data=f"confirm_{auction_id}_{new_price}"), InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid"))
    bot.edit_message_text(f"\u2705 \u062a\u0645 \u0642\u0628\u0648\u0644 \u0627\u0644\u062a\u0639\u0647\u062f!\n\n\u2753 **\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629**\n\u0633\u0648\u0645\u062a\u0643: **{new_price:,} {c}**\n\n\u0647\u0644 \u0623\u0646\u062a \u0645\u062a\u0623\u0643\u062f\u061f", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm_bid(call):
          uid = call.from_user.id
    parts = call.data.split("_")
    auction_id = int(parts[1])
    new_price = int(parts[2])
    auction = database.get_auction(auction_id)
    if not auction or auction['status'] != 'active':
                  bot.answer_callback_query(call.id, "\u26d4 \u0627\u0644\u0645\u0632\u0627\u062f \u0627\u0646\u062a\u0647\u0649!", show_alert=True)
        return
    if new_price <= auction['current_price']:
                  bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0634\u062e\u0635 \u0633\u0628\u0642\u0643! \u0627\u0644\u0633\u0639\u0631 \u0627\u0631\u062a\u0641\u0639\u060b \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.", show_alert=True)
        return
    if auction['highest_bidder'] == uid:
                  bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0623\u0646\u062a \u0628\u0627\u0644\u0641\u0639\u0644 \u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629!", show_alert=True)
        return
    database.place_bid(auction_id, uid, new_price)
    c = cur(auction['currency'])
    bot.edit_message_text(f"\ud83c\udf89 **\u062a\u0645\u062a \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629 \u0628\u0646\u062c\u0627\u062d!**\n\n\u0633\u0648\u0645\u062a\u0643: **{new_price:,} {c}** \u0639\u0644\u0649 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    uname = call.from_user.username or call.from_user.first_name or "\u0645\u062c\u0647\u0648\u0644"
    if len(uname) > 3:
                  uname = uname[:3] + "***"
    bot.send_message(call.message.chat.id, f"\ud83d\udd14 **\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}**\n----------------------------------\n\ud83d\udd25 \u0633\u0648\u0645\u0629 \u062c\u062f\u064a\u062f\u0629: **{new_price:,} {c}**\n\ud83d\udc64 \u0645\u0646: {uname}", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_handler(call):
          uid = call.from_user.id
    auction_id = int(call.data.split("_")[1])
    if not database.has_pledged(uid):
                  database.ensure_user(uid, call.from_user.username or call.from_user.first_name or "\u0645\u062c\u0647\u0648\u0644")
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("\u2705 \u0623\u0648\u0627\u0641\u0642 \u0648\u0623\u062a\u0639\u0647\u062f", callback_data=f"pledgecustom_{auction_id}"))
        markup.row(InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="go_home"))
        bot.send_message(uid, "\u2696\ufe0f **\u062a\u0639\u0647\u062f \u0627\u0644\u0645\u0632\u0627\u062a \u061f \u064a\u062c\u0628 \u0639\u0644\u064a\u0643 \u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0629 \u0639\u0644\u0649 \u0627\u0644\u062a\u0639\u0647\u062f \u0627\u0644\u062a\u0627\u0644\u064a:\n\n\ud83d\udcdc *\u0623\u062a\u0639\u0647\u062f \u0623\u0645\u0627\u0645 \u0627\u0644\u0644\u0647 \u0628\u0627\u0644\u0627\u0644\u062a\u0632\u0627\u0645 \u0628\u062f\u0641\u0639 \u0627\u0644\u0645\u0628\u0644\u063a \u0641\u064a \u062d\u0627\u0644 \u0631\u0633\u0649 \u0627\u0644\u0645\u0632\u0627\u062f \u0639\u0644\u064a.*", reply_markup=markup, parse_mode="Markdown")
        return
    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.answer_callback_query(call.id)
    bot.send_message(uid, f"\u270d\ufe0f \u0627\u0623\u0631\u0633\u0644 \u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0630\u064a \u062a\u0631\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u062a \u0628\u0647:\n(\u064a\u062c\u0628 \u0623\u0646 \u064a\u0643\u0648\u0646 \u0623\u0639\u0644\u0649 \u0645\u0646 {auction['current_price'] + auction['min_increment']:,} {c})")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledgecustom_"))
def pledge_custom(call):
          uid = call.from_user.id
    database.set_pledged(uid)
    auction_id = int(call.data.split("_")[1])
    user_states[uid] = f"CUSTOM_BID_{auction_id}"
    auction = database.get_auction(auction_id)
    c = cur(auction['currency'])
    bot.edit_message_text(f"\u2705 \u062a\u0645 \u0642\u0628\u0648\u0644 \u0627\u0644\u062a\u0639\u0647\u062f!\n\n\u270d\ufe0f \u0627\u0643\u062a\u0628 \u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a:\n(\u0623\u0639\u0644\u0649 \u0645\u0646 {auction['current_price'] + auction['min_increment']:,} {c})", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "cancelbid")
def cancel_bid(call):
          bot.edit_message_text("\u274c \u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auction_handler(call):
          if not database.is_admin(call.from_user.id):
                        bot.answer_callback_query(call.id, "\u26d4 \u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0635\u0644\u0627\u062d\u064a\u0629!", show_alert=True)
                        return
                    auction_id = int(call.data.split("_")[1])
    auction = database.get_auction(auction_id)
    if not auction: return
              database.end_auction(auction_id)
    c = cur(auction['currency'])
    winner = "\u0644\u0627 \u064a\u0648\u062c\u062f \u0641\u0627\u0626\u0632"
    if auction['highest_bidder'] and auction['highest_bidder'] != 0:
                  winner = database.get_username(auction['highest_bidder'])
    bot.send_message(call.message.chat.id, f"\ud83c\udfc6 **\u0627\u0646\u062a\u0647\u0649 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id}!**\n----------------------------------\n\ud83d\udce6 \u0627\u0644\u0633\u0644\u0639\u0629: {auction['title']}\n\ud83d\udcb0 \u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u0646\u0647\u0627\u0626\u064a: **{auction['current_price']:,} {c}**\n\ud83e\udd47 \u0627\u0644\u0641\u0627\u0626\u0632: **@{winner}**\n\n\ud83d\udcde \u064a\u0631\u062c\u0649 \u0627\u0644\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0645\u0627\u0644\u0643 \u0644\u0625\u062a\u0645\u0627\u0645 \u0627\u0644\u0635\u0641\u0642\u0629.", parse_mode="Markdown")
    bot.answer_callback_query(call.id, "\u2705 \u062a\u0645 \u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def currency_select(call):
          uid = call.from_user.id
    currency = call.data.split("_")[1]
    admin_auction_data[uid]["currency"] = currency
    user_states[uid] = "AUC_START_PRICE"
    c = cur(currency)
    bot.edit_message_text(f"\ud83d\udcb0 \u0627\u0644\u062e\u0637\u0648\u0629 4/6: \u0623\u0631\u0633\u0644 **\u0633\u0639\u0631 \u0628\u062f\u0627\u064a\u0629 \u0627\u0644\u0645\u0632\u0627\u062f** \u0628\u0627\u0644\u0640{c}:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
          uid = call.from_user.id
    admin_auction_data[uid]["photo_id"] = None
    _publish_auction(uid)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(message):
          uid = message.from_user.id
    state = user_states.get(uid, "IDLE")
    if state == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
                  try:
                                    new_admin_id = int(message.text.strip())
                                    database.add_admin(new_admin_id)
                                    bot.send_message(uid, f"\u2705 \u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u0631\u0641: `{new_admin_id}`", parse_mode="Markdown")
                                except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 ID \u0635\u062d\u064a\u062d!")
        user_states[uid] = "IDLE"
        return
    if state == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
                  try:
                                    rem_id = int(message.text.strip())
                                    database.remove_admin(rem_id)
                                    bot.send_message(uid, f"\u2705 \u062a\u0645 \u0637\u0631\u062f \u0627\u0644\u0645\u0634\u0631\u0641: `{rem_id}`", parse_mode="Markdown")
                                except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645 ID \u0635\u062d\u064a\u062d!")
        user_states[uid] = "IDLE"
        return
    if state == "AUC_TITLE" and database.is_admin(uid):
                  admin_auction_data[uid] = {"title": message.text.strip()}
        user_states[uid] = "AUC_DESC"
        bot.send_message(uid, "\ud83d\udcdd \u0627\u0644\u062e\u0637\u0648\u0629 2/6: \u0623\u0631\u0633\u0644 **\u0648\u0635\u0641 \u0627\u0644\u0633\u0644\u0639\u0629** (\u0623\u0648 \u0627\u0633\u062a\u062e\u062f\u0645 `-` \u0644\u0644\u062a\u062e\u0637\u064a):", parse_mode="Markdown")
        return
    if state == "AUC_DESC" and database.is_admin(uid):
                  desc = message.text.strip()
        admin_auction_data[uid]["description"] = "" if desc == "-" else desc
        user_states[uid] = "AUC_CURRENCY"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("\ud83c\uddf8\ud83c\udde6 \u0631\u064a\u0627\u0644 \u0633\u0639\u0648\u062f\u064a", callback_data="cur_SAR"), InlineKeyboardButton("\ud83c\uddfa\ud83c\uddf8 \u062f\u0648\u0644\u0627\u0631 \u0623\u0645\u0631\u064a\u0643\u064a", callback_data="cur_USD"))
        bot.send_message(uid, "\ud83d\udcb1 \u0627\u0644\u062e\u0637\u0648\u0629 3/6: \u0627\u062e\u062a\u0631 **\u0639\u0645\u0644\u0629 \u0627\u0644\u0645\u0632\u0627\u062f**:", reply_markup=markup, parse_mode="Markdown")
        return
    if state == "AUC_START_PRICE" and database.is_admin(uid):
                  try:
                                    price = int(message.text.strip())
                                    admin_auction_data[uid]["start_price"] = price
                                    user_states[uid] = "AUC_INCREMENT"
                                    bot.send_message(uid, "\ud83d\udcc8 \u0627\u0644\u062e\u0637\u0648\u0629 5/6: \u0623\u0631\u0633\u0644 **\u0623\u0642\u0644 \u0645\u0628\u0644\u063a \u0632\u064a\u0627\u062f\u0629 \u0645\u0633\u0645\u0648\u062d** (\u0645\u062b\u0627\u0644: 10 \u0623\u0648 50):", parse_mode="Markdown")
                                except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645\u0627\u064b \u0635\u062d\u064a\u062d\u0627\u064b!")
        return
    if state == "AUC_INCREMENT" and database.is_admin(uid):
                  try:
                                    inc = int(message.text.strip())
                                    admin_auction_data[uid]["min_increment"] = inc
                                    user_states[uid] = "AUC_PHOTO"
                                    markup = InlineKeyboardMarkup()
                                    markup.row(InlineKeyboardButton("\u23ed\ufe0f \u062a\u062e\u0637\u064a \u0628\u062f\u0648\u0646 \u0635\u0648\u0631\u0629", callback_data="skip_photo"))
                                    bot.send_message(uid, "\ud83d\udcf8 \u0627\u0644\u062e\u0637\u0648\u0629 6/6: \u0623\u0631\u0633\u0644 **\u0635\u0648\u0631\u0629 \u0627\u0644\u0633\u0644\u0639\u0629** \u0623\u0648 \u0627\u0636\u063a\u0637 \u062a\u062e\u0637\u064a:", reply_markup=markup, parse_mode="Markdown")
                                except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645\u0627\u064b \u0635\u062d\u064a\u062d\u0627\u064b!")
        return
    if state == "AUC_PHOTO" and database.is_admin(uid):
                  if message.photo:
                                    photo_id = message.photo[-1].file_id
                                    admin_auction_data[uid]["photo_id"] = photo_id
                                    _publish_auction(uid)
else:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0635\u0648\u0631\u0629 \u0623\u0648 \u0627\u0636\u063a\u0637 \u062a\u062e\u0637\u064a!")
        return
    if state.startswith("CUSTOM_BID_"):
                  auction_id = int(state.split("_")[2])
        auction = database.get_auction(auction_id)
        if not auction or auction['status'] != 'active':
                          bot.send_message(uid, "\u26d4 \u0627\u0644\u0645\u0632\u0627\u062f \u0645\u0646\u062a\u0647\u064a!")
                          user_states[uid] = "IDLE"
                          return
                      try:
                                        amount = int(message.text.strip())
                                        min_required = auction['current_price'] + auction['min_increment']
                                        if amount < min_required:
                                                              c = cur(auction['currency'])
                                                              bot.send_message(uid, f"\u26a0\ufe0f \u064a\u062c\u0628 \u0623\u0646 \u064a\u0643\u0648\u0646 \u0627\u0644\u0645\u0628\u0644\u063a \u0623\u0639\u0644\u0649 \u0645\u0646 {min_required:,} {c}")
                                                              return
                                                          if auction['highest_bidder'] == uid:
                                                                                bot.send_message(uid, "\u26a0\ufe0f \u0623\u0646\u062a \u0628\u0627\u0644\u0641\u0639\u0644 \u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629!")
                                                                                user_states[uid] = "IDLE"
                                                                                return
                                                                            c = cur(auction['currency'])
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("\u2705 \u062a\u0623\u0643\u064a\u062f", callback_data=f"confirm_{auction_id}_{amount}"), InlineKeyboardButton("\u274c \u0625\u0644\u063a\u0627\u0621", callback_data="cancelbid"))
            bot.send_message(uid, f"\u2753 \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0645\u0632\u0627\u062f \u061f \u0628\u0645\u0628\u0644\u063a **{amount:,} {c}**\u061f", reply_markup=markup, parse_mode="Markdown")
            user_states[uid] = "IDLE"
        except:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645\u0627\u064b \u0635\u062d\u064a\u062d\u0627\u064b \u0641\u0642\u0637!")
        return

def _publish_auction(uid):
          data = admin_auction_data.get(uid, {})
    auction_id = database.create_auction(data.get("title", "\u0628\u062f\u0648\u0646 \u0639\u0646\u0648\u0627\u0646"), data.get("description", ""), data.get("photo_id"), data.get("currency", "SAR"), data.get("start_price", 100), data.get("min_increment", 10))
    auction = database.get_auction(auction_id)
    text = build_auction_text(auction)
    markup = build_bid_buttons(auction)
    markup.row(InlineKeyboardButton("\ud83d\udd34 \u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f", callback_data=f"end_{auction_id}"))
    if data.get("photo_id"):
                  bot.send_photo(uid, data["photo_id"], caption=text, reply_markup=markup, parse_mode="Markdown")
else:
        bot.send_message(uid, text, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(uid, f"\u2705 \u062a\u0645 \u0646\u0634\u0631 \u0627\u0644\u0645\u0632\u0627\u062f #{auction_id} \u0628\u0646\u062c\u0627\u062d!")
    user_states[uid] = "IDLE"
    admin_auction_data.pop(uid, None)

print("\u2705 \u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u064a\u0639\u0645\u0644 \u0627\u0644\u0622\u0646...")

if __name__ == "__main__":
          try:
                        bot.remove_webhook()
                        bot.infinity_polling(timeout=60, long_polling_timeout=60)
except Exception as e:
              print(f"Error: {e}")
      
