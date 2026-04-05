    import os
import threading
import time
import urllib.request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
import database


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, f, *a):
                pass


PORT = int(os.environ.get('PORT', 10000))
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), Handler).serve_forever(), daemon=True).start()

SERVICE_URL = os.environ.get("RENDER_EXTERNAL_URL", "")


def keep_alive():
    while True:
        time.sleep(840)
            if SERVICE_URL:
                    try:
                urllib.request.urlopen(SERVICE_URL)
            except Exception:
                pass


threading.Thread(target=keep_alive, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
bot = telebot.TeleBot(BOT_TOKEN)
database.init_db()
database.set_config("owner_id", str(OWNER_ID))

user_states = {}
auc_data = {}


def gid():
    v = database.get_config("group_id", "0")
    return int(v) if v else 0


def cur(c):
    return "\u0631.\u0633" if c == "SAR" else "$"


def auc_text(a):
    c = cur(a['currency'])
    bn = "\u2014"
    count = database.get_bid_count(a['id'])
    if a['highest_bidder'] and a['highest_bidder'] != 0:
        bn = database.get_username(a['highest_bidder'])
        if len(bn) > 3:
            bn = bn[:3] + ".."
    if a['status'] == 'active':
        st = "\U0001f7e2 \u0645\u0641\u062a\u0648\u062d"
    else:
        st = "\U0001f534 \u0645\u063a\u0644\u0642"
    t = "\U0001f3af *\u0645\u0632\u0627\u062f #" + str(a['id']) + "*\n\n"
    t += "\U0001f4e6 \u0627\u0644\u0633\u0644\u0639\u0629: *" + a['title'] + "*\n"
    if a.get('description'):
        t += "\U0001f4c4 \u0627\u0644\u0648\u0635\u0641: " + a['description'] + "\n"
    t += "\n\U0001f525 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629: *" + f"{a['current_price']:,}" + " " + c + "*\n"
    t += "\U0001f464 \u0635\u0627\u062d\u0628\u0647\u0627: *" + bn + "*\n"
    t += "\U0001f4ca \u0627\u0644\u0633\u0648\u0645\u0627\u062a: *" + str(count) + "*\n"
    t += "\U0001f4a1 \u0627\u0644\u062d\u0627\u0644\u0629: " + st + "\n"
    if a['status'] == 'active':
        t += "\n\u26a0\ufe0f \u0628\u0627\u0644\u0636\u063a\u0637 = \u062a\u0639\u0647\u062f \u0628\u0627\u0644\u062f\u0641\u0639"
    return t


def bid_btns(a):
    m = InlineKeyboardMarkup()
    if a['status'] != 'active':
        return m
    i = a['min_increment']
    d = a['id']
    m.row(
        InlineKeyboardButton("+" + f"{i:,}", callback_data="bid_" + str(d) + "_" + str(i)),
        InlineKeyboardButton("+" + f"{i*2:,}", callback_data="bid_" + str(d) + "_" + str(i*2))
    )
    m.row(
        InlineKeyboardButton("+" + f"{i*5:,}", callback_data="bid_" + str(d) + "_" + str(i*5)),
        InlineKeyboardButton("+" + f"{i*10:,}", callback_data="bid_" + str(d) + "_" + str(i*10))
    )
    m.row(InlineKeyboardButton("\u270d\ufe0f \u0645\u0628\u0644\u063a \u0645\u062e\u0635\u0635", callback_data="custombid_" + str(d)))
    return m


def refresh_grp(aid):
    a = database.get_auction(aid)
    if not a:
                return
    mid = a.get('group_message_id')
    g = gid()
    if not mid or not g:
                return
    try:
        if a.get('photo_id'):
            bot.edit_message_caption(caption=auc_text(a), chat_id=g, message_id=mid, reply_markup=bid_btns(a), parse_mode="Markdown")
        else:
            bot.edit_message_text(auc_text(a), g, mid, reply_markup=bid_btns(a), parse_mode="Markdown")
    except Exception:
                pass


@bot.message_handler(commands=['setgroup'])
def setgroup_cmd(msg):
    if msg.chat.type not in ['group', 'supergroup']:
                return
    if msg.from_user.id != OWNER_ID:
                return
    database.set_config("group_id", str(msg.chat.id))
    bot.reply_to(msg, "\u2705 \u062a\u0645 \u062a\u0639\u064a\u064a\u0646 \u0627\u0644\u0642\u0631\u0648\u0628!")


@bot.message_handler(commands=['start'])
def start_cmd(msg):
    if msg.chat.type != "private":
                return
    uid = msg.from_user.id
    database.ensure_user(uid, msg.from_user.username or msg.from_user.first_name or "user")
    m = InlineKeyboardMarkup()
    if uid == OWNER_ID:
        m.row(InlineKeyboardButton("\U0001f451 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
        m.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    elif database.is_admin(uid):
        m.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
        m.row(InlineKeyboardButton("\u2795 \u0625\u0646\u0634\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    bot.send_message(uid, "\U0001f3af *\u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a*\n\n\u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a \u062a\u0646\u0632\u0644 \u0641\u064a \u0627\u0644\u0642\u0631\u0648\u0628\n\u0632\u0627\u064a\u062f \u0628\u0636\u063a\u0637\u0629 \u0632\u0631", reply_markup=m, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "owner_panel")
def owner_panel(call):
    if call.from_user.id != OWNER_ID:
                return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("\u2795 \u0645\u0634\u0631\u0641", callback_data="add_admin"), InlineKeyboardButton("\u274c \u0637\u0631\u062f", callback_data="remove_admin"))
    m.row(InlineKeyboardButton("\u2795 \u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f", callback_data="create_auction"))
    m.row(InlineKeyboardButton("\U0001f6d1 \u0625\u0646\u0647\u0627\u0621 \u0645\u0632\u0627\u062f", callback_data="end_select"))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="go_home"))
    bot.edit_message_text("\U0001f451 *\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "admin_panel")
def admin_panel(call):
    if not database.is_admin(call.from_user.id):
                return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("\u2795 \u0645\u0632\u0627\u062f", callback_data="create_auction"))
    m.row(InlineKeyboardButton("\U0001f6d1 \u0625\u0646\u0647\u0627\u0621", callback_data="end_select"))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="go_home"))
    bot.edit_message_text("\u2699\ufe0f *\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
    uid = call.from_user.id
    m = InlineKeyboardMarkup()
    if uid == OWNER_ID:
        m.row(InlineKeyboardButton("\U0001f451 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0627\u0644\u0643", callback_data="owner_panel"))
    elif database.is_admin(uid):
        m.row(InlineKeyboardButton("\u2699\ufe0f \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0634\u0631\u0641", callback_data="admin_panel"))
    bot.edit_message_text("\U0001f3af *\u0628\u0648\u062a \u0627\u0644\u0645\u0632\u0627\u062f\u0627\u062a*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_h(call):
    if call.from_user.id != OWNER_ID:
            return
    user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("\U0001f46e \u0623\u0631\u0633\u0644 \u0622\u064a\u062f\u064a \u0627\u0644\u0645\u0634\u0631\u0641:", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_h(call):
    if call.from_user.id != OWNER_ID:
        return
    user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("\U0001f6ab \u0623\u0631\u0633\u0644 \u0622\u064a\u062f\u064a \u0627\u0644\u0645\u0634\u0631\u0641:", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data == "create_auction")
def create_auc(call):
    uid = call.from_user.id
    if not database.is_admin(uid):
        return
    if gid() == 0:
        bot.answer_callback_query(call.id, "\u26d4 \u0623\u0631\u0633\u0644 /setgroup \u0641\u064a \u0627\u0644\u0642\u0631\u0648\u0628 \u0623\u0648\u0644\u0627!", show_alert=True)
        return
    user_states[uid] = "AUC_TITLE"
    auc_data[uid] = {}
    bot.edit_message_text("\U0001f4e6 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (1/6)\n\n\u0623\u0631\u0633\u0644 \u0627\u0633\u0645 \u0627\u0644\u0633\u0644\u0639\u0629:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "end_select")
def end_select(call):
    if not database.is_admin(call.from_user.id):
        return
    aucs = database.get_active_auctions()
    if not aucs:
        bot.answer_callback_query(call.id, "\u0644\u0627 \u0645\u0632\u0627\u062f\u0627\u062a!", show_alert=True)
        return
    m = InlineKeyboardMarkup()
    for a in aucs:
        c = cur(a['currency'])
        lbl = "#" + str(a['id']) + " " + a['title'] + " (" + f"{a['current_price']:,}" + " " + c + ")"
        m.row(InlineKeyboardButton(lbl, callback_data="end_" + str(a['id'])))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="go_home"))
    bot.edit_message_text("\U0001f6d1 *\u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u0632\u0627\u062f:*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
    uid = call.from_user.id
    un = call.from_user.username or call.from_user.first_name or "user"
    database.ensure_user(uid, un)
    p = call.data.split("_")
    aid = int(p[1])
    ba = int(p[2])
    a = database.get_auction(aid)
    if not a or a['status'] != 'active':
        bot.answer_callback_query(call.id, "\u26d4 \u0645\u063a\u0644\u0642!", show_alert=True)
        return
    if a['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "\u26a0\ufe0f \u0623\u0646\u062a \u0635\u0627\u062d\u0628 \u0623\u0639\u0644\u0649 \u0633\u0648\u0645\u0629!", show_alert=True)
        return
    np = a['current_price'] + ba
    c = cur(a['currency'])
    prev = a['highest_bidder']
    database.set_pledged(uid)
    database.place_bid(aid, uid, np)
    bot.answer_callback_query(call.id, "\u2705 \u062a\u0645! \u0633\u0648\u0645\u062a\u0643: " + f"{np:,}" + " " + c, show_alert=True)
    refresh_grp(aid)
    g = gid()
    if g:
        name = un if len(un) <= 3 else un[:3] + ".."
        try:
            bot.send_message(g, "\U0001f514 *\u0633\u0648\u0645\u0629 \u062c\u062f\u064a\u062f\u0629* | #" + str(aid) + " | *" + f"{np:,}" + " " + c + "* | " + name, parse_mode="Markdown")
        except Exception:
                    pass
    if prev and prev != 0 and prev != uid:
        try:
            bot.send_message(prev, "\U0001f514 \u062a\u0645 \u0643\u0633\u0631 \u0633\u0648\u0645\u062a\u0643 #" + str(aid) + " | \u0627\u0644\u062c\u062f\u064a\u062f: *" + f"{np:,}" + " " + c + "*", parse_mode="Markdown")
        except Exception:
                    pass
    # Send last 2 bids to owner
    last2 = database.get_last_bids(aid, 2)
    if last2:
            txt = "\U0001f4cb *\u0622\u062e\u0631 \u0645\u0632\u0627\u064a\u062f\u0627\u062a #" + str(aid) + ":*\n"
            for b in last2:
            bname = database.get_username(b['tg_id'])
            txt += "\u2022 @" + bname + " : *" + f"{b['amount']:,}" + " " + c + "*\n"
        try:
            bot.send_message(OWNER_ID, txt, parse_mode="Markdown")
        except Exception:
                    pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_h(call):
    uid = call.from_user.id
    aid = int(call.data.split("_")[1])
    database.ensure_user(uid, call.from_user.username or "user")
    database.set_pledged(uid)
    user_states[uid] = "CUSTOM_BID_" + str(aid)
    a = database.get_auction(aid)
    c = cur(a['currency'])
    mn = a['current_price'] + a['min_increment']
        bot.answer_callback_query(call.id)
        try:
        bot.send_message(uid, "\u270d\ufe0f \u0627\u0643\u062a\u0628 \u0627\u0644\u0645\u0628\u0644\u063a (\u0623\u0639\u0644\u0649 \u0645\u0646 " + f"{mn:,}" + " " + c + "):")
        except Exception:
                pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auc(call):
    if not database.is_admin(call.from_user.id):
        return
    aid = int(call.data.split("_")[1])
    a = database.get_auction(aid)
    if not a:
        return
    database.end_auction(aid)
    c = cur(a['currency'])
    w = "\u0644\u0627 \u0641\u0627\u0626\u0632"
    winner_id = 0
    if a['highest_bidder'] and a['highest_bidder'] != 0:
        w = "@" + database.get_username(a['highest_bidder'])
        winner_id = a['highest_bidder']
    count = database.get_bid_count(aid)
    last2 = database.get_last_bids(aid, 2)
    # Group message
    g = gid()
    if g:
        gt = "\U0001f534 *\u062a\u0645 \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0645\u0632\u0627\u062f #" + str(aid) + "*\n\n"
        gt += "\U0001f4e6 " + a['title'] + "\n"
        gt += "\U0001f4b0 \u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u0646\u0647\u0627\u0626\u064a: *" + f"{a['current_price']:,}" + " " + c + "*\n"
        gt += "\U0001f4ca \u0627\u0644\u0633\u0648\u0645\u0627\u062a: " + str(count) + "\n"
        gt += "\U0001f947 \u0627\u0644\u0641\u0627\u0626\u0632: *" + w + "*\n\n"
        gt += "\U0001f389 \u0645\u0628\u0627\u0631\u0643 \u0644\u0644\u0645\u0634\u062a\u0631\u064a! \u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0628\u0627\u0626\u0639"
        try:
            bot.send_message(g, gt, parse_mode="Markdown")
        except Exception:
            pass
    refresh_grp(aid)
    # Winner message
    if winner_id:
        try:
            bot.send_message(winner_id, "\U0001f389 *\u0645\u0628\u0627\u0631\u0643!*\n\u0631\u0633\u0649 \u0639\u0644\u064a\u0643 \u0627\u0644\u0645\u0632\u0627\u062f #" + str(aid) + "\n*" + f"{a['current_price']:,}" + " " + c + "*\n\n\u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u0628\u0627\u0626\u0639 \u0644\u0625\u062a\u0645\u0627\u0645 \u0627\u0644\u0635\u0641\u0642\u0629", parse_mode="Markdown")
        except Exception:
            pass
    # Owner report
    ot = "\U0001f4cb *\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0645\u0632\u0627\u062f #" + str(aid) + "*\n\n"
    ot += "\U0001f4e6 " + a['title'] + "\n"
    ot += "\U0001f4b0 \u0627\u0644\u0646\u0647\u0627\u0626\u064a: *" + f"{a['current_price']:,}" + " " + c + "*\n"
    ot += "\U0001f947 \u0627\u0644\u0641\u0627\u0626\u0632: *" + w + "*\n"
    ot += "\U0001f4ca \u0627\u0644\u0633\u0648\u0645\u0627\u062a: " + str(count) + "\n\n"
    if last2:
        ot += "*\u0622\u062e\u0631 \u0645\u0632\u0627\u064a\u062f\u0627\u062a:*\n"
        for b in last2:
            bname = database.get_username(b['tg_id'])
            ot += "\u2022 @" + bname + " : *" + f"{b['amount']:,}" + " " + c + "*\n"
    try:
        bot.send_message(OWNER_ID, ot, parse_mode="Markdown")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "\u2705 \u062a\u0645!")


@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def cur_select(call):
    uid = call.from_user.id
    cy = call.data.split("_")[1]
    auc_data[uid]["currency"] = cy
    user_states[uid] = "AUC_START_PRICE"
    c = cur(cy)
    bot.edit_message_text("\U0001f4b0 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (4/6)\n\n\u0633\u0639\u0631 \u0627\u0644\u0628\u062f\u0627\u064a\u0629 \u0628\u0627\u0644" + c + ":", call.message.chat.id, call.message.message_id, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
    auc_data[call.from_user.id]["photo_id"] = None
    publish(call.from_user.id)


@bot.message_handler(content_types=['text', 'photo'])
def handle_all(msg):
        uid = msg.from_user.id
    if msg.chat.type != "private":
        return
    st = user_states.get(uid, "IDLE")
    if st == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
        try:
            nid = int(msg.text.strip())
            database.add_admin(nid)
            bot.send_message(uid, "\u2705 \u062a\u0645 \u0625\u0636\u0627\u0641\u0629 " + str(nid))
        except Exception:
            bot.send_message(uid, "\u274c \u0631\u0642\u0645 \u063a\u0644\u0637")
        user_states[uid] = "IDLE"
        return
    if st == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
        try:
            rid = int(msg.text.strip())
            database.remove_admin(rid)
            bot.send_message(uid, "\u2705 \u062a\u0645 \u0637\u0631\u062f " + str(rid))
        except Exception:
            bot.send_message(uid, "\u274c \u0631\u0642\u0645 \u063a\u0644\u0637")
        user_states[uid] = "IDLE"
        return
    if st == "AUC_TITLE" and database.is_admin(uid):
        auc_data[uid] = {"title": msg.text.strip()}
        user_states[uid] = "AUC_DESC"
        bot.send_message(uid, "\U0001f4c4 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (2/6)\n\n\u0648\u0635\u0641 \u0627\u0644\u0633\u0644\u0639\u0629 (\u0623\u0648 - \u0644\u0644\u062a\u062e\u0637\u064a):", parse_mode="Markdown")
        return
    if st == "AUC_DESC" and database.is_admin(uid):
        d = msg.text.strip()
        auc_data[uid]["description"] = "" if d == "-" else d
        user_states[uid] = "AUC_CURRENCY"
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("\U0001f1f8\U0001f1e6 \u0631\u064a\u0627\u0644", callback_data="cur_SAR"), InlineKeyboardButton("\U0001f1fa\U0001f1f8 \u062f\u0648\u0644\u0627\u0631", callback_data="cur_USD"))
        bot.send_message(uid, "\U0001f4b1 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (3/6)\n\n\u0627\u062e\u062a\u0631 \u0627\u0644\u0639\u0645\u0644\u0629:", reply_markup=mk, parse_mode="Markdown")
        return
    if st == "AUC_START_PRICE" and database.is_admin(uid):
        try:
            auc_data[uid]["start_price"] = int(msg.text.strip())
            user_states[uid] = "AUC_INCREMENT"
            bot.send_message(uid, "\U0001f4c8 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (5/6)\n\n\u0623\u0642\u0644 \u0632\u064a\u0627\u062f\u0629 (\u0645\u062b\u0627\u0644: 10):", parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645!")
            return
    if st == "AUC_INCREMENT" and database.is_admin(uid):
        try:
            auc_data[uid]["min_increment"] = int(msg.text.strip())
            user_states[uid] = "AUC_PHOTO"
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("\u23ed\ufe0f \u062a\u062e\u0637\u064a", callback_data="skip_photo"))
            bot.send_message(uid, "\U0001f4f8 *\u0645\u0632\u0627\u062f \u062c\u062f\u064a\u062f* (6/6)\n\n\u0635\u0648\u0631\u0629 \u0623\u0648 \u062a\u062e\u0637\u064a:", reply_markup=mk, parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, "\u274c \u0623\u0631\u0633\u0644 \u0631\u0642\u0645!")
            return
    if st == "AUC_PHOTO" and database.is_admin(uid):
        if msg.photo:
            auc_data[uid]["photo_id"] = msg.photo[-1].file_id
            publish(uid)
            return
    if st.startswith("CUSTOM_BID_"):
        aid = int(st.split("_")[2])
        a = database.get_auction(aid)
        if not a or a['status'] != 'active':
            user_states[uid] = "IDLE"
            return
        try:
            amt = int(msg.text.strip())
            mn = a['current_price'] + a['min_increment']
            if amt < mn:
                c = cur(a['currency'])
                bot.send_message(uid, "\u26a0\ufe0f \u064a\u062c\u0628 " + f"{mn:,}" + "+")
                return
            if a['highest_bidder'] == uid:
                user_states[uid] = "IDLE"
                return
            prev = a['highest_bidder']
            database.place_bid(aid, uid, amt)
            c = cur(a['currency'])
            bot.send_message(uid, "\u2705 \u062a\u0645! *" + f"{amt:,}" + " " + c + "*", parse_mode="Markdown")
            user_states[uid] = "IDLE"
            refresh_grp(aid)
            g = gid()
            un = msg.from_user.username or msg.from_user.first_name or "user"
            name = un if len(un) <= 3 else un[:3] + ".."
            if g:
                try:
                    bot.send_message(g, "\U0001f514 *\u0633\u0648\u0645\u0629 \u062c\u062f\u064a\u062f\u0629* | #" + str(aid) + " | *" + f"{amt:,}" + " " + c + "* | " + name, parse_mode="Markdown")
                except Exception:
                    pass
            if prev and prev != 0 and prev != uid:
                try:
                    bot.send_message(prev, "\U0001f514 \u0643\u0633\u0631 \u0633\u0648\u0645\u062a\u0643 #" + str(aid) + " | *" + f"{amt:,}" + " " + c + "*", parse_mode="Markdown")
                except Exception:
                    pass
            last2 = database.get_last_bids(aid, 2)
            if last2:
                txt = "\U0001f4cb *\u0622\u062e\u0631 \u0645\u0632\u0627\u064a\u062f\u0627\u062a #" + str(aid) + ":*\n"
                for b in last2:
                    bname = database.get_username(b['tg_id'])
                    txt += "\u2022 @" + bname + " : *" + f"{b['amount']:,}" + " " + c + "*\n"
                try:
                    bot.send_message(OWNER_ID, txt, parse_mode="Markdown")
                except Exception:
                    pass
        except Exception:
            bot.send_message(uid, "\u274c \u0623\u0631\u0642\u0627\u0645 \u0641\u0642\u0637!")
        return


def publish(uid):
    d = auc_data.get(uid, {})
    aid = database.create_auction(d.get("title", ""), d.get("description", ""), d.get("photo_id"), d.get("currency", "SAR"), d.get("start_price", 100), d.get("min_increment", 10))
    a = database.get_auction(aid)
    g = gid()
    try:
        if d.get("photo_id"):
            sent = bot.send_photo(g, d["photo_id"], caption=auc_text(a), reply_markup=bid_btns(a), parse_mode="Markdown")
        else:
            sent = bot.send_message(g, auc_text(a), reply_markup=bid_btns(a), parse_mode="Markdown")
        database.set_auction_group_msg(aid, sent.message_id)
        bot.send_message(uid, "\u2705 \u062a\u0645 \u0646\u0634\u0631 \u0627\u0644\u0645\u0632\u0627\u062f #" + str(aid) + "!")
    except Exception as e:
        bot.send_message(uid, "\u274c " + str(e))
    user_states[uid] = "IDLE"
    auc_data.pop(uid, None)


print("\u2705 Bot running...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Error: " + str(e))
