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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)
database.set_config("owner_id", str(OWNER_ID))
user_states = {}
admin_auction_data = {}

def cur(currency):
      return "SAR" if currency == "SAR" else "$"

def build_auction_text(a):
      c = cur(a['currency'])
    bn = "None"
    if a['highest_bidder'] and a['highest_bidder'] != 0:
              bn = database.get_username(a['highest_bidder'])
              if len(bn) > 3: bn = bn[:3] + "***"
                    st = "Active" if a['status'] == 'active' else "Ended"
    t = f"Auction #{a['id']}\n"
    t += f"Item: {a['title']}\n"
    if a.get('description'): t += f"Desc: {a['description']}\n"
          t += f"Start: {a['start_price']:,} {c}\n"
    t += f"Min Inc: {a['min_increment']:,} {c}\n"
    t += f"Current: {a['current_price']:,} {c}\n"
    t += f"Highest: {bn}\n"
    t += f"Status: {st}\n"
    return t

def build_bid_buttons(a):
      m = InlineKeyboardMarkup()
    if a['status'] != 'active': return m
          i = a['min_increment']
    d = a['id']
    m.row(InlineKeyboardButton(f"+{i:,}", callback_data=f"bid_{d}_{i}"), InlineKeyboardButton(f"+{i*2:,}", callback_data=f"bid_{d}_{i*2}"))
    m.row(InlineKeyboardButton(f"+{i*5:,}", callback_data=f"bid_{d}_{i*5}"), InlineKeyboardButton("Custom", callback_data=f"custombid_{d}"))
    return m

@bot.message_handler(commands=['start'])
def start_cmd(msg):
      uid = msg.from_user.id
    un = msg.from_user.username or msg.from_user.first_name or "user"
    database.ensure_user(uid, un)
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("Auctions", callback_data="list_auctions"))
    if uid == OWNER_ID:
              m.row(InlineKeyboardButton("Owner Panel", callback_data="owner_panel"))
        m.row(InlineKeyboardButton("New Auction", callback_data="create_auction"))
elif database.is_admin(uid):
        m.row(InlineKeyboardButton("Admin Panel", callback_data="admin_panel"))
    bot.send_message(uid, "Welcome to Auction Bot!", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "owner_panel")
def owner_panel(call):
      if call.from_user.id != OWNER_ID: return
            m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("Add Admin", callback_data="add_admin"))
    m.row(InlineKeyboardButton("Remove Admin", callback_data="remove_admin"))
    m.row(InlineKeyboardButton("New Auction", callback_data="create_auction"))
    m.row(InlineKeyboardButton("Back", callback_data="go_home"))
    bot.edit_message_text("Owner Panel", call.message.chat.id, call.message.message_id, reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
      if not database.is_admin(call.from_user.id): return
            m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("New Auction", callback_data="create_auction"))
    m.row(InlineKeyboardButton("Back", callback_data="go_home"))
    bot.edit_message_text("Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
      uid = call.from_user.id
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("Auctions", callback_data="list_auctions"))
    if uid == OWNER_ID: m.row(InlineKeyboardButton("Owner", callback_data="owner_panel"))
elif database.is_admin(uid): m.row(InlineKeyboardButton("Admin", callback_data="admin_panel"))
    bot.edit_message_text("Auction Bot", call.message.chat.id, call.message.message_id, reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_h(call):
      if call.from_user.id != OWNER_ID: return
            user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("Send admin Telegram ID:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_h(call):
      if call.from_user.id != OWNER_ID: return
            user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("Send admin ID to remove:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "create_auction")
def create_auction_h(call):
      uid = call.from_user.id
    if not database.is_admin(uid): return
          user_states[uid] = "AUC_TITLE"
    admin_auction_data[uid] = {}
    bot.edit_message_text("Step 1/6: Send item name:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "list_auctions")
def list_auctions_h(call):
      aucs = database.get_active_auctions()
    if not aucs:
              bot.answer_callback_query(call.id, "No auctions!", show_alert=True)
              return
          for a in aucs:
                    t = build_auction_text(a)
                    mk = build_bid_buttons(a)
                    if database.is_admin(call.from_user.id):
                                  mk.row(InlineKeyboardButton("End Auction", callback_data=f"end_{a['id']}"))
                              if a.get('photo_id'):
                                            bot.send_photo(call.message.chat.id, a['photo_id'], caption=t, reply_markup=mk)
else:
            bot.send_message(call.message.chat.id, t, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
      uid = call.from_user.id
    database.ensure_user(uid, call.from_user.username or "user")
    p = call.data.split("_")
    aid = int(p[1])
    ba = int(p[2])
    a = database.get_auction(aid)
    if not a or a['status'] != 'active':
              bot.answer_callback_query(call.id, "Ended!", show_alert=True)
        return
    if a['highest_bidder'] == uid:
              bot.answer_callback_query(call.id, "Already highest!", show_alert=True)
        return
    if not database.has_pledged(uid):
              mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("I Pledge", callback_data=f"pledge_{aid}_{ba}"))
        mk.row(InlineKeyboardButton("Cancel", callback_data="go_home"))
        bot.send_message(uid, "Pledge required before bidding. Do you agree?", reply_markup=mk)
        return
    np = a['current_price'] + ba
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("Confirm", callback_data=f"confirm_{aid}_{np}"), InlineKeyboardButton("Cancel", callback_data="cancelbid"))
    c = cur(a['currency'])
    bot.answer_callback_query(call.id)
    bot.send_message(uid, f"Confirm bid: {np:,} {c}?", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledge_"))
def handle_pledge(call):
      uid = call.from_user.id
    database.set_pledged(uid)
    p = call.data.split("_")
    aid = int(p[1])
    ba = int(p[2])
    a = database.get_auction(aid)
    if not a or a['status'] != 'active': return
          np = a['current_price'] + ba
    c = cur(a['currency'])
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("Confirm", callback_data=f"confirm_{aid}_{np}"), InlineKeyboardButton("Cancel", callback_data="cancelbid"))
    bot.edit_message_text(f"Pledged! Confirm: {np:,} {c}?", call.message.chat.id, call.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_"))
def confirm_bid(call):
      uid = call.from_user.id
    p = call.data.split("_")
    aid = int(p[1])
    np = int(p[2])
    a = database.get_auction(aid)
    if not a or a['status'] != 'active': return
          if np <= a['current_price']:
                    bot.answer_callback_query(call.id, "Outbid!", show_alert=True)
        return
    if a['highest_bidder'] == uid: return
          database.place_bid(aid, uid, np)
    c = cur(a['currency'])
    bot.edit_message_text(f"Bid placed: {np:,} {c} on #{aid}", call.message.chat.id, call.message.message_id)
    un = call.from_user.username or "user"
    if len(un) > 3: un = un[:3] + "***"
          bot.send_message(call.message.chat.id, f"New bid on #{aid}: {np:,} {c} by {un}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_h(call):
      uid = call.from_user.id
    aid = int(call.data.split("_")[1])
    if not database.has_pledged(uid):
              database.ensure_user(uid, call.from_user.username or "user")
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("I Pledge", callback_data=f"pledgecustom_{aid}"))
        bot.send_message(uid, "Pledge required.", reply_markup=mk)
        return
    user_states[uid] = f"CUSTOM_BID_{aid}"
    a = database.get_auction(aid)
    c = cur(a['currency'])
    bot.answer_callback_query(call.id)
    bot.send_message(uid, f"Enter bid amount (min: {a['current_price']+a['min_increment']:,} {c}):")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pledgecustom_"))
def pledge_custom(call):
      uid = call.from_user.id
    database.set_pledged(uid)
    aid = int(call.data.split("_")[1])
    user_states[uid] = f"CUSTOM_BID_{aid}"
    a = database.get_auction(aid)
    c = cur(a['currency'])
    bot.edit_message_text(f"Pledged! Enter amount (min: {a['current_price']+a['min_increment']:,} {c}):", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "cancelbid")
def cancel_bid(call):
      bot.edit_message_text("Cancelled.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auction_h(call):
      if not database.is_admin(call.from_user.id): return
            aid = int(call.data.split("_")[1])
    a = database.get_auction(aid)
    if not a: return
          database.end_auction(aid)
    c = cur(a['currency'])
    w = "No winner"
    if a['highest_bidder'] and a['highest_bidder'] != 0:
              w = database.get_username(a['highest_bidder'])
    bot.send_message(call.message.chat.id, f"Auction #{aid} ended!\nItem: {a['title']}\nFinal: {a['current_price']:,} {c}\nWinner: @{w}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def currency_select(call):
      uid = call.from_user.id
    cy = call.data.split("_")[1]
    admin_auction_data[uid]["currency"] = cy
    user_states[uid] = "AUC_START_PRICE"
    c = cur(cy)
    bot.edit_message_text(f"Step 4/6: Send starting price in {c}:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
      uid = call.from_user.id
    admin_auction_data[uid]["photo_id"] = None
    _publish_auction(uid)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(msg):
      uid = msg.from_user.id
    st = user_states.get(uid, "IDLE")
    if st == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
              try:
                            nid = int(msg.text.strip())
                            database.add_admin(nid)
                            bot.send_message(uid, f"Added admin: {nid}")
                        except: bot.send_message(uid, "Invalid ID!")
        user_states[uid] = "IDLE"
        return
    if st == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
              try:
                            rid = int(msg.text.strip())
                            database.remove_admin(rid)
                            bot.send_message(uid, f"Removed: {rid}")
                        except: bot.send_message(uid, "Invalid ID!")
        user_states[uid] = "IDLE"
        return
    if st == "AUC_TITLE" and database.is_admin(uid):
              admin_auction_data[uid] = {"title": msg.text.strip()}
        user_states[uid] = "AUC_DESC"
        bot.send_message(uid, "Step 2/6: Send description (or - to skip):")
        return
    if st == "AUC_DESC" and database.is_admin(uid):
              d = msg.text.strip()
        admin_auction_data[uid]["description"] = "" if d == "-" else d
        user_states[uid] = "AUC_CURRENCY"
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("SAR", callback_data="cur_SAR"), InlineKeyboardButton("USD", callback_data="cur_USD"))
        bot.send_message(uid, "Step 3/6: Choose currency:", reply_markup=mk)
        return
    if st == "AUC_START_PRICE" and database.is_admin(uid):
              try:
                            p = int(msg.text.strip())
                            admin_auction_data[uid]["start_price"] = p
                            user_states[uid] = "AUC_INCREMENT"
                            bot.send_message(uid, "Step 5/6: Send min increment:")
                        except: bot.send_message(uid, "Invalid!")
        return
    if st == "AUC_INCREMENT" and database.is_admin(uid):
              try:
                            inc = int(msg.text.strip())
                            admin_auction_data[uid]["min_increment"] = inc
                            user_states[uid] = "AUC_PHOTO"
                            mk = InlineKeyboardMarkup()
                            mk.row(InlineKeyboardButton("Skip", callback_data="skip_photo"))
                            bot.send_message(uid, "Step 6/6: Send photo or skip:", reply_markup=mk)
                        except: bot.send_message(uid, "Invalid!")
        return
    if st == "AUC_PHOTO" and database.is_admin(uid):
              if msg.photo:
                            admin_auction_data[uid]["photo_id"] = msg.photo[-1].file_id
                            _publish_auction(uid)
else: bot.send_message(uid, "Send photo or skip!")
        return
    if st.startswith("CUSTOM_BID_"):
              aid = int(st.split("_")[2])
        a = database.get_auction(aid)
        if not a or a['status'] != 'active':
                      bot.send_message(uid, "Ended!")
                      user_states[uid] = "IDLE"
                      return
                  try:
                                amt = int(msg.text.strip())
                                mn = a['current_price'] + a['min_increment']
                                if amt < mn:
                                                  bot.send_message(uid, f"Must be above {mn:,}")
                                                  return
                                              if a['highest_bidder'] == uid:
                                                                user_states[uid] = "IDLE"
                                                                return
                                                            c = cur(a['currency'])
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("Confirm", callback_data=f"confirm_{aid}_{amt}"), InlineKeyboardButton("Cancel", callback_data="cancelbid"))
            bot.send_message(uid, f"Confirm: {amt:,} {c}?", reply_markup=mk)
            user_states[uid] = "IDLE"
        except: bot.send_message(uid, "Numbers only!")
        return

def _publish_auction(uid):
      d = admin_auction_data.get(uid, {})
    aid = database.create_auction(d.get("title","Untitled"), d.get("description",""), d.get("photo_id"), d.get("currency","SAR"), d.get("start_price",100), d.get("min_increment",10))
    a = database.get_auction(aid)
    t = build_auction_text(a)
    mk = build_bid_buttons(a)
    mk.row(InlineKeyboardButton("End Auction", callback_data=f"end_{aid}"))
    if d.get("photo_id"):
              bot.send_photo(uid, d["photo_id"], caption=t, reply_markup=mk)
else:
        bot.send_message(uid, t, reply_markup=mk)
    bot.send_message(uid, f"Auction #{aid} published!")
    user_states[uid] = "IDLE"
    admin_auction_data.pop(uid, None)

print("Bot running...")
if __name__ == "__main__":
      try:
                bot.remove_webhook()
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
except Exception as e:
          print(f"Error: {e}")
  
