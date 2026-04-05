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

def scheduler_loop():
    while True:
        try:
            now = time.time()
            # 1. Start scheduled auctions
            sched_aucs = database.get_scheduled_auctions()
            for a in sched_aucs:
                if a['scheduled_start_time'] <= now:
                    aid = a['id']
                    end_tm = a.get('end_time', 0)
                    if end_tm <= 0:
                        end_tm = now + (a.get('duration_minutes', 5) * 60)
                    database.set_auction_active(aid, end_tm)
                    a['status'] = 'active'
                    a['end_time'] = end_tm
                    g = gid()
                    if g:
                        try:
                            m = bid_btns(a)
                            if a.get('photo_id'):
                                sent = bot.send_photo(g, a['photo_id'], caption=auc_text(a), reply_markup=m, parse_mode="Markdown")
                            else:
                                sent = bot.send_message(g, auc_text(a), reply_markup=m, parse_mode="Markdown")
                            database.set_auction_group_msg(aid, sent.message_id)
                            bot.pin_chat_message(g, sent.message_id, disable_notification=False)
                        except Exception as e:
                            print("Pin/Send Error:", e)
            
            # 2. Check active auctions for end or refresh
            act_aucs = database.get_active_auctions()
            for a in act_aucs:
                if a.get('end_time') and a['end_time'] > 0:
                    aid = a['id']
                    if a['end_time'] <= now:
                        # Auto End Auction
                        call = type('obj', (object,), {'data': f'end_{aid}', 'from_user': type('obj', (object,), {'id': OWNER_ID})(), 'id': "0"})()
                        end_auc(call)
                        g = gid()
                        mid = a.get('group_message_id')
                        if g and mid:
                            try:
                                bot.unpin_chat_message(g, mid)
                            except:
                                pass
                    elif int(now) % 60 == 0:
                        refresh_grp(aid)
        except Exception as e:
            pass
        time.sleep(10)

threading.Thread(target=scheduler_loop, daemon=True).start()

user_states = {}
auc_data = {}
req_data = {}

def gid():
    v = database.get_config("group_id", "0")
    return int(v) if v else 0

def cur(c):
    return "ر.س" if c == "SAR" else "$"

def auc_text(a):
    c = cur(a['currency'])
    bn = "\u2014"
    count = database.get_bid_count(a['id'])
    if a['highest_bidder'] and a['highest_bidder'] != 0:
        bn = "@" + database.get_username(a['highest_bidder'])
    st = ""
    if a['status'] == 'active':
        if a.get('end_time') and a['end_time'] > 0:
            rem = int(a['end_time'] - time.time())
            if rem > 0:
                mins, secs = divmod(rem, 60)
                st = "\U0001f7e2 مفتوح (باقي: " + f"{mins:02d}:{secs:02d}" + ")"
            else:
                st = "\U0001f7e2 مفتوح (ينتهي الآن...)"
        else:
            st = "\U0001f7e2 مفتوح"
    elif a['status'] == 'scheduled':
        st_tm = a.get('scheduled_start_time', 0)
        lt = time.gmtime(st_tm + 10800)
        st = f"\u23f2\ufe0f مجدول - يبدأ الساعة {lt.tm_hour:02d}:{lt.tm_min:02d} (لمدة {a.get('duration_minutes', 5)} دقيقة)"
    else:
        st = "\U0001f534 مغلق"
        
    seller = a.get('seller_username', '')
    t = f"\U0001f3af *مزاد #{a['id']}*\n\n"
    t += f"\U0001f4e6 السلعة: *{a['title']}*\n"
    if a.get('description'):
        t += f"\U0001f4c4 الوصف: {a['description']}\n"
    if seller:
        t += f"\U0001f464 البائع: @{seller}\n"
    t += f"\n\U0001f525 أعلى سومة: *{'{:,}'.format(a['current_price'])} {c}*\n"
    t += f"\U0001f464 صاحبها: {bn}\n"
    t += f"\U0001f4ca السومات: *{count}*\n"
    t += f"\U0001f4a1 الحالة: {st}\n"
    if a['status'] == 'active':
        t += "\n\u26a0\ufe0f بالضغط = تعهد بالدفع"
    return t

def bid_btns(a):
    m = InlineKeyboardMarkup()
    if a['status'] != 'active': return m
    i = a['min_increment']
    d = a['id']
    m.row(InlineKeyboardButton("+" + "{:,}".format(i), callback_data=f"bid_{d}_{i}"), InlineKeyboardButton("+" + "{:,}".format(i*2), callback_data=f"bid_{d}_{i*2}"))
    m.row(InlineKeyboardButton("+" + "{:,}".format(i*5), callback_data=f"bid_{d}_{i*5}"), InlineKeyboardButton("+" + "{:,}".format(i*10), callback_data=f"bid_{d}_{i*10}"))
    m.row(InlineKeyboardButton("\u270d\ufe0f مبلغ مخصص", callback_data=f"custombid_{d}"))
    return m

def refresh_grp(aid):
    a = database.get_auction(aid)
    if not a: return
    mid = a.get('group_message_id')
    g = gid()
    if not mid or not g: return
    try:
        if a.get('photo_id'):
            bot.edit_message_caption(caption=auc_text(a), chat_id=g, message_id=mid, reply_markup=bid_btns(a), parse_mode="Markdown")
        else:
            bot.edit_message_text(auc_text(a), g, mid, reply_markup=bid_btns(a), parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=['setgroup'])
def setgroup_cmd(msg):
    if msg.chat.type not in ['group', 'supergroup']: return
    if msg.from_user.id != OWNER_ID: return
    database.set_config("group_id", str(msg.chat.id))
    bot.reply_to(msg, "\u2705 تم تعيين القروب!")

@bot.message_handler(commands=['agenda'])
def agenda_cmd(msg):
    aucs = database.get_scheduled_auctions()
    if not aucs:
        bot.reply_to(msg, "\u274c لا يوجد مزادات مجدولة لليوم.")
        return
    t = "\U0001f4c5 *جدول مزادات اليوم:*\n\n"
    for i, a in enumerate(aucs, 1):
        lt = time.gmtime(a.get('scheduled_start_time', 0) + 10800)
        t += f"{i}\u20e3 *{a['title']}*\n \u251c البائع: @{a['seller_username']}\n \u2514 الموعد: {lt.tm_hour:02d}:{lt.tm_min:02d}\n\n"
    bot.reply_to(msg, t, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_cmd(msg):
    if msg.chat.type != "private": return
    uid = msg.from_user.id
    database.ensure_user(uid, msg.from_user.username or msg.from_user.first_name or "user")
    m = InlineKeyboardMarkup()
    if database.get_config("reg_status", "open") == "open":
        m.row(InlineKeyboardButton("\U0001f4e6 طلب مزاد", callback_data="new_request"))
    else:
        m.row(InlineKeyboardButton("\u26d4 التسجيل مغلق لليوم", callback_data="closed_reg_msg"))
        
    if uid == OWNER_ID:
        m.row(InlineKeyboardButton("\U0001f451 لوحة المالك", callback_data="owner_panel"))
    elif database.is_admin(uid):
        m.row(InlineKeyboardButton("\u2699\ufe0f لوحة المشرف", callback_data="admin_panel"))
    bot.send_message(uid, "\U0001f3af *بوت المزادات الآلي*\n\nتُعرض هنا مزادات النخبة", reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "closed_reg_msg")
def closed_reg_msg(call):
    bot.answer_callback_query(call.id, "عذراً، انتهى وقت التسجيل لمزادات اليوم! انتظرونا غداً.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "new_request")
def new_request(call):
    if database.get_config("reg_status", "open") != "open":
        bot.answer_callback_query(call.id, "\u26d4 عذراً، تم إقفال التسجيل لمزادات اليوم!", show_alert=True)
        return
    uid = call.from_user.id
    user_states[uid] = "REQ_TITLE"
    req_data[uid] = {}
    bot.edit_message_text("\U0001f4e6 *طلب مزاد جديد*\n\nالخطوة 1/6\nاكتب اسم السلعة:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data in ["owner_panel", "admin_panel"])
def panels(call):
    uid = call.from_user.id
    if call.data == "owner_panel" and uid != OWNER_ID: return
    if call.data == "admin_panel" and not database.is_admin(uid): return
    
    pending = database.get_pending_count()
    appr = len(database.get_approved_requests())
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(f"\U0001f4cb الطلبات ({pending})", callback_data="view_requests"))
    
    if database.get_config("reg_status", "open") == "open":
        m.row(InlineKeyboardButton(f"\U0001f4c5 إغلاق وجدولة اليوم ({appr} مقبول)", callback_data="close_and_schedule"))
    else:
        m.row(InlineKeyboardButton("\U0001f513 فتح التسجيل للغد", callback_data="open_registration"))
        
    m.row(InlineKeyboardButton("\U0001f6d1 إنهاء مزاد", callback_data="end_select"))
    if call.data == "owner_panel":
        m.row(InlineKeyboardButton("\u2795 مشرف", callback_data="add_admin"), InlineKeyboardButton("\u274c طرد", callback_data="remove_admin"))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="go_home"))
    
    bot.edit_message_text(f"*\U0001f451 لوحة الإدارة*\n\n" + ("\U0001f7e2 التسجيل مفتوح" if database.get_config("reg_status", "open") == "open" else "\U0001f534 التسجيل مغلق"), call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def go_home(call):
    start_cmd(call.message)

@bot.callback_query_handler(func=lambda c: c.data == "view_requests")
def view_requests(call):
    if not database.is_admin(call.from_user.id): return
    reqs = database.get_pending_requests()
    if not reqs:
        bot.answer_callback_query(call.id, "لا طلبات معلقة!", show_alert=True)
        return
    m = InlineKeyboardMarkup()
    for r in reqs:
        lbl = f"#{r['id']} {r['title']} (@{r['seller_username']})"
        m.row(InlineKeyboardButton(lbl, callback_data=f"showreq_{r['id']}"))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="owner_panel"))
    bot.edit_message_text("\U0001f4cb *الطلبات المعلقة:*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("showreq_"))
def show_request(call):
    if not database.is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[1])
    r = database.get_request(rid)
    if not r: return
    c = cur(r['currency'])
    t = f"\U0001f4cb *طلب #{r['id']}*\n\n\U0001f4e6 السلعة: *{r['title']}*\n"
    if r['description']: t += f"\U0001f4c4 الوصف: {r['description']}\n"
    t += f"\U0001f464 البائع: @{r['seller_username']}\n\U0001f4b0 البداية: {'{:,}'.format(r['start_price'])} {c}\n\U0001f4c8 الزيادة: {'{:,}'.format(r['min_increment'])} {c}\n\U0001f464 الطالب: @{r['requester_username']}\n"
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("\u2705 قبول (سينتظر الجدولة)", callback_data=f"approve_{rid}"), InlineKeyboardButton("\u274c رفض", callback_data=f"reject_{rid}"))
    mk.row(InlineKeyboardButton("\U0001f519", callback_data="view_requests"))
    bot.edit_message_text(t, call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve_req(call):
    if not database.is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[1])
    database.approve_request(rid)
    bot.edit_message_text(f"\u2705 تم قبول الطلب #{rid} وإضافته לקﺎئمة اليوم (بانتظار جدولة اليوم).", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject_req(call):
    if not database.is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[1])
    r = database.get_request(rid)
    if not r: return
    database.reject_request(rid)
    try: bot.send_message(r['requester_id'], f"\u274c *تم رفض طلبك #{rid}*", parse_mode="Markdown")
    except: pass
    bot.edit_message_text(f"\u274c تم رفض الطلب #{rid}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "open_registration")
def open_registration(call):
    if not database.is_admin(call.from_user.id): return
    database.set_config("reg_status", "open")
    bot.answer_callback_query(call.id, "\u2705 تم فتح التسجيل للمزادات!", show_alert=True)
    panels(call)

@bot.callback_query_handler(func=lambda c: c.data == "close_and_schedule")
def close_and_schedule(call):
    if not database.is_admin(call.from_user.id): return
    appr = database.get_approved_requests()
    if not appr:
        bot.answer_callback_query(call.id, "\u26d4 لا يوجد طلبات مقبولة لجدولتها!", show_alert=True)
        return
    uid = call.from_user.id
    user_states[uid] = "GLOBAL_SCHED_TIME"
    bot.edit_message_text(f"\u23f0 **تحديد موعد بداية مزادات اليوم**\n\nسيتم جدولة {len(appr)} مزاد، مدة كل מזאد 5 دقائق.\n\nأدخل وقت البداية بصيغة 24 ساعة (مثال: 21:00):", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def add_admin_h(call):
    if call.from_user.id != OWNER_ID: return
    user_states[call.from_user.id] = "WAIT_ADD_ADMIN"
    bot.edit_message_text("\U0001f46e أرسل آيدي المشرف:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_h(call):
    if call.from_user.id != OWNER_ID: return
    user_states[call.from_user.id] = "WAIT_REMOVE_ADMIN"
    bot.edit_message_text("\U0001f6ab أرسل آيدي المشرف:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "end_select")
def end_select(call):
    if not database.is_admin(call.from_user.id): return
    aucs = database.get_active_auctions()
    if not aucs:
        bot.answer_callback_query(call.id, "لا مزادات شغالة!", show_alert=True)
        return
    m = InlineKeyboardMarkup()
    for a in aucs:
        c = cur(a['currency'])
        m.row(InlineKeyboardButton(f"#{a['id']} {a['title']} ({'{:,}'.format(a['current_price'])} {c})", callback_data=f"end_{a['id']}"))
    m.row(InlineKeyboardButton("\U0001f519", callback_data="owner_panel"))
    bot.edit_message_text("\U0001f6d1 *اختر لتنهي فوراً:*", call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("bid_"))
def handle_bid(call):
    uid = call.from_user.id
    un = call.from_user.username or call.from_user.first_name or "user"
    database.ensure_user(uid, un)
    p = call.data.split("_")
    aid, ba = int(p[1]), int(p[2])
    a = database.get_auction(aid)
    if not a or a['status'] != 'active':
        bot.answer_callback_query(call.id, "\u26d4 مغلق!", show_alert=True)
        return
    if a['highest_bidder'] == uid:
        bot.answer_callback_query(call.id, "\u26a0\ufe0f أنت الأعلى!", show_alert=True)
        return
    np = a['current_price'] + ba
    database.set_pledged(uid)
    database.place_bid(aid, uid, np)
    bot.answer_callback_query(call.id, f"\u2705 تمت سومتك: {'{:,}'.format(np)} {cur(a['currency'])}", show_alert=True)
    refresh_grp(aid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("custombid_"))
def custom_bid_h(call):
    uid = call.from_user.id
    aid = int(call.data.split("_")[1])
    database.ensure_user(uid, call.from_user.username or "user")
    database.set_pledged(uid)
    user_states[uid] = f"CUSTOM_BID_{aid}"
    a = database.get_auction(aid)
    bot.answer_callback_query(call.id)
    try: bot.send_message(uid, f"\u270d\ufe0f اكتب المبلغ (أعلى من {'{:,}'.format(a['current_price'] + a['min_increment'])} {cur(a['currency'])}):")
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("end_"))
def end_auc(call):
    aid = int(call.data.split("_")[1])
    a = database.get_auction(aid)
    if not a or a['status'] == 'ended': return
    database.end_auction(aid)
    c = cur(a['currency'])
    w, winner_id = "لا فائز", 0
    if a['highest_bidder'] and a['highest_bidder'] != 0:
        w = "@" + database.get_username(a['highest_bidder'])
        winner_id = a['highest_bidder']
    count = database.get_bid_count(aid)
    seller = a.get('seller_username', '')
    g = gid()
    if g:
        gt = f"\U0001f534 *تم انتهاء المزاد #{aid}*\n\n\U0001f4e6 {a['title']}\n\U0001f4b0 السعر النهائي: *{'{:,}'.format(a['current_price'])} {c}*\n\U0001f4ca السومات: {count}\n\U0001f947 الفائز: *{w}*\n"
        if seller: gt += f"\n\U0001f4de تواصل مع البائع @{seller}"
        try: bot.send_message(g, gt, parse_mode="Markdown")
        except: pass
    refresh_grp(aid)
    if winner_id:
        wt = f"\U0001f389 *مبارك!*\nرسى عليك #{aid}\n*{'{:,}'.format(a['current_price'])} {c}*\n"
        if seller: wt += f"تواصل مع البائع: @{seller}"
        try: bot.send_message(winner_id, wt, parse_mode="Markdown")
        except: pass
    
    # Notify Owner
    ot = f"\U0001f4cb *تقرير #{aid}*\n\n\U0001f4e6 {a['title']}\n\U0001f4b0 {'{:,}'.format(a['current_price'])} {c}\n\U0001f947 {w}\n"
    last2 = database.get_last_bids(aid, 2)
    if last2:
        ot += "\n*آخر مزايدات:*\n"
        for b in last2:
            ot += f"• @{database.get_username(b['tg_id'])} : {'{:,}'.format(b['amount'])} {c}\n"
    try: bot.send_message(OWNER_ID, ot, parse_mode="Markdown")
    except: pass
    try: bot.answer_callback_query(call.id, "\u2705 تم الانتهاء!")
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("cur_"))
def cur_select(call):
    uid, cy = call.from_user.id, call.data.split("_")[1]
    req_data[uid]["currency"] = cy
    user_states[uid] = "REQ_START_PRICE"
    bot.edit_message_text(f"\U0001f4b0 *طلب مزاد* (5/6)\n\nسعر البداية بالـ {cur(cy)}:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
def skip_photo(call):
    uid = call.from_user.id
    req_data[uid]["photo_id"] = None
    submit_request(uid)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(msg):
    uid = msg.from_user.id
    if msg.chat.type != "private": return
    st = user_states.get(uid, "IDLE")
    
    if st == "WAIT_ADD_ADMIN" and uid == OWNER_ID:
        try: database.add_admin(int(msg.text.strip())); bot.send_message(uid, "\u2705 تم")
        except: bot.send_message(uid, "\u274c خطأ")
        user_states[uid] = "IDLE"; return
    if st == "WAIT_REMOVE_ADMIN" and uid == OWNER_ID:
        try: database.remove_admin(int(msg.text.strip())); bot.send_message(uid, "\u2705 تم")
        except: bot.send_message(uid, "\u274c خطأ")
        user_states[uid] = "IDLE"; return

    if st == "REQ_TITLE":
        req_data[uid] = {"title": msg.text.strip()}
        user_states[uid] = "REQ_DESC"
        bot.send_message(uid, "\U0001f4c4 *طلب مزاد* (2/6)\n\nوصف السلعة (أو - للتخطي):", parse_mode="Markdown"); return
    if st == "REQ_DESC":
        req_data[uid]["description"] = "" if msg.text.strip() == "-" else msg.text.strip()
        user_states[uid] = "REQ_SELLER"
        bot.send_message(uid, "\U0001f464 *طلب مزاد* (3/6)\n\nيوزر صاحب السلعة (بدون @):", parse_mode="Markdown"); return
    if st == "REQ_SELLER":
        req_data[uid]["seller_username"] = msg.text.strip().replace("@", "")
        user_states[uid] = "REQ_CURRENCY"
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("ريال", callback_data="cur_SAR"), InlineKeyboardButton("$ دولار", callback_data="cur_USD"))
        bot.send_message(uid, "\U0001f4b1 *طلب مزاد* (4/6)\n\nاختر العملة:", reply_markup=mk, parse_mode="Markdown"); return
    if st == "REQ_START_PRICE":
        try: req_data[uid]["start_price"] = int(msg.text.strip())
        except: bot.send_message(uid, "\u274c رقم!"); return
        user_states[uid] = "REQ_INCREMENT"
        bot.send_message(uid, "\U0001f4c8 *طلب مزاد* (6/6)\n\nأقل زيادة (مثال: 10):", parse_mode="Markdown"); return
    if st == "REQ_INCREMENT":
        try: req_data[uid]["min_increment"] = int(msg.text.strip())
        except: bot.send_message(uid, "\u274c رقم!"); return
        user_states[uid] = "REQ_PHOTO"
        mk = InlineKeyboardMarkup().row(InlineKeyboardButton("\u23ed\ufe0f تخطي", callback_data="skip_photo"))
        bot.send_message(uid, "\U0001f4f8 أرسل صورة أو تخطي:", reply_markup=mk); return
    if st == "REQ_PHOTO":
        if msg.photo:
            req_data[uid]["photo_id"] = msg.photo[-1].file_id
            submit_request(uid)
        return

    if st.startswith("CUSTOM_BID_"):
        aid = int(st.split("_")[2])
        a = database.get_auction(aid)
        if not a or a['status'] != 'active':
            user_states[uid] = "IDLE"; return
        try:
            amt = int(msg.text.strip())
            mn = a['current_price'] + a['min_increment']
            if amt < mn:
                bot.send_message(uid, f"\u26a0\ufe0f يجب السوم بأعلى من {'{:,}'.format(mn)}")
                return
            if a['highest_bidder'] == uid: return
            database.place_bid(aid, uid, amt)
            bot.send_message(uid, f"\u2705 *{'{:,}'.format(amt)} {cur(a['currency'])}*", parse_mode="Markdown")
            user_states[uid] = "IDLE"
            refresh_grp(aid)
        except:
            bot.send_message(uid, "\u274c أرقام خطأ!")
        return

    # Global Schedule Logic
    if st == "GLOBAL_SCHED_TIME" and database.is_admin(uid):
        try:
            h, m = map(int, msg.text.strip().split(":"))
            if not(0 <= h <= 23 and 0 <= m <= 59): raise ValueError
            now_epoch = time.time()
            ksa_struct = time.gmtime(now_epoch + 10800)
            ksa_midnight = now_epoch - (ksa_struct.tm_hour * 3600 + ksa_struct.tm_min * 60 + ksa_struct.tm_sec)
            target_epoch = ksa_midnight + (h * 3600) + (m * 60)
            if target_epoch <= now_epoch: target_epoch += 86400
            
            database.set_config("reg_status", "closed")
            appr = database.get_approved_requests()
            curr = target_epoch
            
            agenda_txt = "\U0001f4c5 *جدول مزادات اليوم!*\n\nستبدأ المزادات بالترتيب (كل مزاد 5 دقائق):\n\n"
            for i, r in enumerate(appr, 1):
                aid = database.create_auction(r['title'], r['description'], r['photo_id'], r['currency'], r['start_price'], r['min_increment'], r['seller_username'], r['id'], curr, 5, 'scheduled')
                database.mark_request_scheduled(r['id'])
                lt = time.gmtime(curr + 10800)
                agenda_txt += f"{i}\u20e3 *{r['title']}*\n \u251c البائع: @{r['seller_username']}\n \u2514 الوقت: {lt.tm_hour:02d}:{lt.tm_min:02d}\n\n"
                try: bot.send_message(r['requester_id'], f"\u2705 *تم جدولة مزادك!*\nسيبدأ الساعة {lt.tm_hour:02d}:{lt.tm_min:02d}", parse_mode="Markdown")
                except: pass
                curr += 300
            
            bot.send_message(uid, f"\u2705 تمت جدولة {len(appr)} مزاد، وإقفال التسجيل لليوم.")
            g = gid()
            if g:
                try: bot.send_message(g, agenda_txt, parse_mode="Markdown")
                except: pass
            user_states[uid] = "IDLE"
        except:
            bot.send_message(uid, "\u274c صيغة خاطئة! استخدم HH:MM")
        return

def submit_request(uid):
    d = req_data.get(uid, {})
    try: un = (bot.get_chat(uid).username or "user")
    except: un = "user"
    rid = database.create_request(uid, un, d.get("seller_username", ""), d.get("title", ""), d.get("description", ""), d.get("photo_id"), d.get("currency", "SAR"), d.get("start_price", 100), d.get("min_increment", 10))
    pos = database.get_queue_position(rid)
    bot.send_message(uid, f"\u2705 *تم رفع طلبك!*\n\n\U0001f4cb رقم الطلب: #{rid}\n\U0001f4ca دورك: {pos}\n\nيتم تدقيقه واعتماده للجدولة.", parse_mode="Markdown")
    try: bot.send_message(OWNER_ID, f"\U0001f4e8 *طلب جديد #{rid}*\n{d.get('title', '')} | @{d.get('seller_username', '')}", parse_mode="Markdown")
    except: pass
    user_states[uid] = "IDLE"
    req_data.pop(uid, None)

print("\u2705 Bot running...")
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Error:", e)
