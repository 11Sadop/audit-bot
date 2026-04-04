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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)
database.set_config("owner_id", str(OWNER_ID))

user_states = {}

def cur(currency):
      return "\u0631\u064a\u0627\u0644" if currency == "SAR" else "$"

def build_auction_text(auction):
      c = cur(auction['currency'])
      bidder_name = "\u0644\u0627 \u064a\u0648\u062c\u062f \u0628\u0639\u062f"
      if auction['highest_bidder'] and auction['highest_bidder'] != 0:
                bidder_name = database.get_username(auction['highest_bidder'])
                if len(bidder_name) > 3:
                              bidder_name = bidder_name[:3] + "***"

            status_emoji = "\u2705 \u062c\u0627\u0631\u064a" if auction['status'] == 'active' else "\ud83d\udd34 \u0645\u0646\u062a\u0647\u064a"
    text = f"\ud83c\udff7\ufe0f **\u0645\u0632\u0627\u062f \u0631\u0642\u0645 #{auction['id']}**\n"
    text += f"----------------------------------\n"
    text += f"\ud83d\udce6 **\u0627\u0644\u0633\u0644\u0631\u0629:** {auction['title']}\n"
    if auction.get('description'):
              text += f"\ud83d\udcdd **\u0648\u0635\u0641:** {auction['description']}\n"
          text += f"\ud83d\udcb0 **\u0633\u0631\u0631 \u0627\u0644\u0627\u0641\u062a\u062a\u0627\u062d:** {auction['start_price']:,} {c}\n"
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
              InlineKeyboardButton(f"+{inc:,}", callback_data=f"bid_{aid}_{inc}"),
              InlineKeyboardButton(f"+{inc*2:,}", callback_data=f"bid_{aid}_{inc*2}")
    )
    markup.row(
              InlineKeyboardButton(f"+{inc*5:,}", callback_data=f"bid_{aid}_{inc*5}"),
              InlineKeyboardButton("\u0645\u0628\u0644\u063a \u0645\u062e\u0635\u0635", callback_data=f"custombid_{aid}")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
      uid = message.from_user.id
    username = message.from_user.first_name
    database.add_user(uid, username)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("\ud83c\udfd8\ufe0f \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u0627\u0644\u0646\u0634\u0637\u0629", callback_data="list_active"))

    is_admin = (uid == OWNER_ID) or database.is_admin(uid)
    if is_admin:
              markup.add(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="admin_new_auction"))
              markup.add(InlineKeyboardButton("\u2699\ufe0f \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0634\u0631\u0641\u064a\u0646", callback_data="admin_list_admins"))

    bot.send_message(message.chat.id, f"\u0623\u0647\u0644\u0627\u064b \u0628\u0643 \u064a\u0627 {username} \u0641\u064a \u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a! \ud83d\ude80", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
      uid = call.from_user.id
      if call.data == "list_active":
                auctions = database.get_active_auctions()
                if not auctions:
                              bot.answer_callback_query(call.id, "\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0632\u0627\u062f\u0627\u062a \u0646\u0634\u0637\u0629 \u062d\u0627\u0644\u064a\u0627\u064b.")
                              return
                          for a in auctions:
                                        bot.send_message(call.message.chat.id, build_auction_text(a), reply_markup=build_bid_buttons(a), parse_mode="Markdown")

elif call.data.startswith("bid_"):
        parts = call.data.split("_")
        aid, amount = int(parts[1]), int(parts[2])
        auction = database.get_auction(aid)
        if not auction or auction['status'] != 'active':
                      bot.answer_callback_query(call.id, "\u0631\u0630\u0631\u0627\u064b\u060b \u0647\u0630\u0627 \u0627\u0644\u0645\u0632\u0627\u062f \u0642\u062f \u0627\u0646\u062a\u0647\u0649.")
                      return

        new_price = auction['current_price'] + amount
        database.place_bid(aid, uid, new_price)
        updated_auction = database.get_auction(aid)
        bot.edit_message_text(build_auction_text(updated_auction), call.message.chat.id, call.message.message_id, reply_markup=build_bid_buttons(updated_auction), parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"\u062a\u0645\u062a \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629 \u0628\u0646\u062c\u0627\u062d! \u0627\u0644\u0633\u0631\u0631 \u0627\u0644\u062d\u0627\u0644\u064a: {new_price:,}")

elif call.data.startswith("custombid_"):
        aid = int(call.data.split("_")[1])
        user_states[uid] = {'action': 'waiting_custom_bid', 'auction_id': aid}
        bot.send_message(call.message.chat.id, "\u0623\u0631\u0633\u0644 \u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0630\u064a \u062a\u0631\u063a\u0628 \u0641\u064a \u0627\u0644\u0645\u0632\u0627\u064a\u062f\u0629 \u0628\u0647:")

elif call.data == "admin_new_auction":
        if uid != OWNER_ID and not database.is_admin(uid): return
                  user_states[uid] = {'action': 'waiting_auction_title'}
        bot.send_message(call.message.chat.id, "\u0623\u0631\u0633\u0644 \u0631\u0646\u0648\u0627\u0646 \u0627\u0644\u0633\u0644\u0631\u0629:")

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_states(m):
      uid = m.from_user.id
      state = user_states[uid]

    if state['action'] == 'waiting_custom_bid':
              try:
                            val = int(m.text)
                            aid = state['auction_id']
                            auction = database.get_auction(aid)
                            if val < auction['current_price'] + auction['min_increment']:
                                              bot.reply_to(m, "\u0627\u0644\u0645\u0628\u0644\u063a \u0642\u0644\u064a\u0644 \u062c\u062f\u0627\u064b!")
                                              return
                                          database.place_bid(aid, uid, val)
                            bot.reply_to(m, "\u062a\u0645 \u0642\u0628\u0648\u0644 \u0633\u0648\u0645\u062a\u0643! \u2705")
                            del user_states[uid]
                        except:
            bot.reply_to(m, "\u064a\u0631\u062c\u0649 \u0625\u0631\u0633\u0627\u0644 \u0631\u0642\u0645 \u0635\u062d\u064a\u062d.")

elif state['action'] == 'waiting_auction_title':
        state['title'] = m.text
        state['action'] = 'waiting_auction_price'
        bot.send_message(m.chat.id, "\u0623\u0631\u0633\u0644 \u0633\u0631\u0631 \u0627\u0644\u0627\u0641\u062a\u062a\u0627\u062d:")

elif state['action'] == 'waiting_auction_price':
        try:
                      state['price'] = int(m.text)
                      state['action'] = 'waiting_auction_inc'
                      bot.send_message(m.chat.id, "\u0623\u0631\u0633\u0644 \u0623\u0642\u0644 \u0632\u064a\u0627\u062f\u0629:")
                  except: bot.reply_to(m, "\u0631\u0642\u0645 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d.")

elif state['action'] == 'waiting_auction_inc':
        try:
                      inc = int(m.text)
                      database.create_auction(state['title'], state['price'], inc, OWNER_ID)
                      bot.send_message(m.chat.id, f"\u2705 \u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f: {state['title']}")
                      del user_states[uid]
                  except: bot.reply_to(m, "\u0631\u0642\u0645 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d.")

if __name__ == "__main__":
      bot.infinity_polling()
