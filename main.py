from datetime import datetime
import sqlite3
import telebot
import requests
import os
from flask import Flask, render_template_string
from threading import Thread

# ==========================================
# بوت الإمبراطور المحترف - النسخة المعدلة لتعمل على Render بنجاح 👑
# ==========================================

TOKEN = "8870951794:AAHCEODY8KC-lYgHA8M6XJJYjoijX9eqQx0"
CHANNEL_NAME = "@EmperorSMS_Channel"
SMSPOOL_API_KEY = "Rsc8VKD2r6P0bk1A8WbObJZ7BOLL3F0v"
DEVELOPER_USERNAME = "geedallh"

bot = telebot.TeleBot(TOKEN)

# ==========================================
# إعداد خادم ويب وهمي لضمان عمل البوت على Render 24/7
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Emperor Bot is active and running 24/7! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==========================================
# إعداد قاعدة البيانات الشاملة (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("emperor_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            invited_by INTEGER DEFAULT NULL,
            referrals_count INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            service_name TEXT,
            country_name TEXT,
            phone_number TEXT,
            price REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_data(user_id):
    conn = sqlite3.connect("emperor_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    else:
        conn = sqlite3.connect("emperor_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0.0))
        conn.commit()
        conn.close()
        return 0.0, 0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect("emperor_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ==========================================
# دوال الاتصال بـ API موقع SMSPool (مربوطة بالكامل)
# ==========================================
def smspool_buy_number(country_id, service_id):
    url = "https://api.smspool.net/purchase/sms"
    params = {
        "key": SMSPOOL_API_KEY,
        "country": country_id,
        "service": service_id,
        "pricing": "1"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("success") == 1:
            return data
        else:
            return None
    except Exception as e:
        print(f"Error buying number: {e}")
        return None

def smspool_check_sms(order_id):
    url = "https://api.smspool.net/sms/check"
    params = {"key": SMSPOOL_API_KEY, "orderid": order_id}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Error checking SMS: {e}")
        return None

def smspool_cancel_order(order_id):
    url = "https://api.smspool.net/purchase/cancel"
    params = {"key": SMSPOOL_API_KEY, "orderid": order_id}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Error canceling order: {e}")
        return None

# ==========================================
# دالة نشر العمليات في القناة الرسمية
# ==========================================
def send_to_channel(service_name, country_name, phone_number, price, user_id, sms_code="-----"):
    try:
        current_time = datetime.now().strftime("%A %d يوليو %Y | %I:%M:%S %p")
        masked_user = f"***{str(user_id)[-4:]}"
        
        channel_text = (
            f"⚜️ تفعيلات الشراء - الإمبراطور 🔥\n"
            f"-----------------------------------\n"
            f"🎛️ - السيرفر : العروض الآلية (SMSPool)\n"
            f"🌍 - الدولة : {country_name}\n"
            f"📱 - تطبيق : {service_name}\n"
            f"📞 - الرقم : `+{phone_number}`\n"
            f"💰 - السعر : {price} ₽\n"
            f"🆔 - العميل : `{masked_user}`\n"
            f"📧 - رسالة الكود : [ `{sms_code}` ] 💡\n"
            f"-----------------------------------\n"
            f"📅 - {current_time}\n\n"
            f"☑️ : تم شراء رقم من البوت بنجاح 🔊"
        )
        
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("🤖 - شراء رقم من البوت ↗", url=f"https://t.me/{bot.get_me().username}")
        markup.add(btn)
        
        bot.send_message(CHANNEL_NAME, channel_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error posting to channel: {e}")

# ==========================================
# أمر البدء (Start) والقائمة الرئيسية
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    balance, _ = get_user_data(user_id)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            inviter_id = int(args[1].split("_")[1])
            if inviter_id != user_id:
                conn = sqlite3.connect("emperor_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT invited_by FROM users WHERE user_id = ?", (user_id,))
                res = cursor.fetchone()
                if res and res[0] is None:
                    cursor.execute("UPDATE users SET invited_by = ? WHERE user_id = ?", (inviter_id, user_id))
                    cursor.execute("UPDATE users SET balance = balance + 0.3, referrals_count = referrals_count + 1 WHERE user_id = ?", (inviter_id,))
                    conn.commit()
                    bot.send_message(inviter_id, "🎉 **مبارك!** دخل شخص جديد عبر رابط الدعوة الخاص بك وتمت إضافة `0.3` روبل إلى رصيدك.", parse_mode="Markdown")
                conn.close()
        except Exception as e:
            print(f"Ref error: {e}")

    welcome_text = (
        f"☑️ - مرحبا بك في القائمة الرئيسية\n"
        f"⚜️ - لدى بوت الإمبراطور | SMS العالمي ⚜️\n\n"
        f"👮 - اهلا بك عزيزي : {user_name} 🤍\n"
        f"📭 - حسابك : `ID_{user_id}@Emperor.com` ✉️\n\n"
        f"💰 - رصيد حسابك الان : {balance:.2f} ₽ 💰\n"
        f"🕹️ - اخر الاخبار ⬇️\n"
        f"جلب تلقائي لجميع خدمات ودول منصة SMSPool 😍❤️\n"
        f"🔄 - تحكم الان بضغط على الازرار بالاسفل ⬇️"
    )

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn1 = telebot.types.InlineKeyboardButton("🎲 الرشق والحسابات التليجرام 👥", callback_data="boost")
    btn2 = telebot.types.InlineKeyboardButton("🔥 عروض تليجرام 🚀", callback_data="offers_tg")
    btn3 = telebot.types.InlineKeyboardButton("🛍️ عروض واتساب 🚀", callback_data="offers_wa")
    btn4 = telebot.types.InlineKeyboardButton("📞 شراء أرقام شاملة (تلقائي) ☎️", callback_data="dynamic_services")
    btn5 = telebot.types.InlineKeyboardButton("💰 شحن حسابك 💻", callback_data="charge")
    btn6 = telebot.types.InlineKeyboardButton("🗄️ سجل الحساب ☑️", callback_data="history")
    btn7 = telebot.types.InlineKeyboardButton("🌐 خدمات الموقع الشاملة 🔄", callback_data="dynamic_services")
    btn8 = telebot.types.InlineKeyboardButton("👮 طلب المساعدة ⚠️", callback_data="support")
    btn9 = telebot.types.InlineKeyboardButton("🌟 خدمات ومميزات 💥", callback_data="features")
    btn10 = telebot.types.InlineKeyboardButton("🎁 قسم اربح روبل (دعوة أصدقاء)", callback_data="ref_section")
    btn11 = telebot.types.InlineKeyboardButton("🛡️ الإدارة العليا والمطور 🏛", callback_data="developer")
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10, btn11)
    
    try:
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# ==========================================
# معالج الأزرار والتفاعل بالكامل
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    back_markup = telebot.types.InlineKeyboardMarkup()
    back_markup.add(telebot.types.InlineKeyboardButton("🔙 - العودة للقائمة", callback_data="back_home"))

    # --- عروض تليجرام ---
    if call.data == "offers_tg" or call.data.startswith("tg_page_"):
        page = 0
        if call.data.startswith("tg_page_"):
            page = int(call.data.split("_")[2])
        
        bot.answer_callback_query(call.id, "فتح قسم عروض تليجرام")
        
        countries_list = [
            ("🇺🇸 أمريكا", "us", "10 ₽", "us", "telegram"), ("🇷🇺 روسيا", "ru", "9 ₽", "ru", "telegram"),
            ("🇹🇷 تركيا", "tr", "10 ₽", "tr", "telegram"), ("🇪🇬 مصر", "eg", "13 ₽", "eg", "telegram"),
            ("🇸🇦 السعودية", "sa", "13 ₽", "sa", "telegram"), ("🇾🇪 اليمن", "ye", "15 ₽", "ye", "telegram"),
            ("🇩🇪 ألمانيا", "de", "5 ₽", "de", "telegram"), ("🇧🇷 البرازيل", "br", "9 ₽", "br", "telegram"),
            ("🇮🇩 إندونيسيا", "id", "15 ₽", "id", "telegram"), ("🇰🇼 الكويت", "kw", "15 ₽", "kw", "telegram"),
            ("🇨🇦 كندا", "ca", "10 ₽", "ca", "telegram"), ("🇲🇦 المغرب", "ma", "10 ₽", "ma", "telegram")
        ]
        
        items_per_page = 6
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_slice = countries_list[start_idx:end_idx]
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        row_buttons = []
        for c_name, c_code, price, api_c, api_s in current_slice:
            row_buttons.append(telebot.types.InlineKeyboardButton(f"{c_name} : {price}", callback_data=f"buy_real_{api_c}_{api_s}_10"))
        
        markup.add(*row_buttons)
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(telebot.types.InlineKeyboardButton("⬅️ السابق", callback_data=f"tg_page_{page-1}"))
        if end_idx < len(countries_list):
            nav_buttons.append(telebot.types.InlineKeyboardButton("التالي ➡️", callback_data=f"tg_page_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
            
        markup.add(telebot.types.InlineKeyboardButton("🔙 - العودة للقائمة", callback_data="back_home"))
        
        text = "☑️ **- مرحبا بك في القسم أكثر توفراً (عروض تليجرام)**\n\nاختر الدولة المطلوبة للشراء:"
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except:
            pass

    # --- عروض واتساب ---
    elif call.data == "offers_wa":
        bot.answer_callback_query(call.id, "فتح عروض واتساب")
        countries_list = [
            ("🇺🇸 أمريكا", "us", "10 ₽", "us", "whatsapp"), ("🇮🇩 إندونيسيا", "id", "15 ₽", "id", "whatsapp"),
            ("🇹🇷 تركيا", "tr", "10 ₽", "tr", "whatsapp"), ("🇧🇷 البرازيل", "br", "9 ₽", "br", "whatsapp")
        ]
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        for c_name, c_code, price, api_c, api_s in countries_list:
            markup.add(telebot.types.InlineKeyboardButton(f"{c_name} : {price}", callback_data=f"buy_real_{api_c}_{api_s}_10"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 - العودة للقائمة", callback_data="back_home"))
        bot.edit_message_text("🛍️ **اختر الدولة لتفعيل واتساب:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # --- تنفيذ عملية الشراء الحقيقي من SMSPool ---
    elif call.data.startswith("buy_real_"):
        parts = call.data.split("_")
        country_code = parts[2]
        service_code = parts[3]
        cost = float(parts[4])

        balance, _ = get_user_data(user_id)
        if balance < cost:
            bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ لشراء الرقم!", show_alert=True)
            return

        bot.answer_callback_query(call.id, "⏳ جاري إرسال الطلب إلى السيرفر وحجز الرقم...")
        
        api_result = smspool_buy_number(country_code, service_code)
        
        if not api_result or "phonenumber" not in api_result:
            bot.answer_callback_query(call.id, "❌ عذراً، لا توجد أرقام متاحة حالياً لهذه الدولة حاول لاحقاً.", show_alert=True)
            return

        update_user_balance(user_id, -cost)
        
        phone = api_result.get("phonenumber")
        order_id = str(api_result.get("orderid"))

        conn = sqlite3.connect("emperor_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO orders (order_id, user_id, service_name, country_name, phone_number, price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (order_id, user_id, service_code, country_code, phone, cost, "pending"))
        conn.commit()
        conn.close()

        success_text = (
            f"🟩 **- تم شراء الرقم بنجاح!**\n\n"
            f"☑️ **- الدولة: {country_code.upper()}**\n"
            f"☑️ **- البرنامج: {service_code.upper()}**\n\n"
            f"☎️ - الرقم: `+{phone}`\n"
            f"💬 - الكود: Waiting ...\n"
            f"🌀 - الحالة: Waiting ...\n"
            f"💰 - السعر: {cost} ₽\n\n"
            f"☑️ - إضغط على الرقم لنسخه.!\n"
            f"🟢 - أدخل الرقم في التطبيق لوصول الكود.!\n"
            f"⚜️ - إضغط على تحديث ليصلك الكود الحقيقي.!"
        )
        
        control_markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        control_markup.add(
            telebot.types.InlineKeyboardButton("🌐 - رؤية في التطبيق", url=f"https://wa.me/{phone}"),
            telebot.types.InlineKeyboardButton("🔄 - تحديث", callback_data=f"check_sms_{order_id}"),
            telebot.types.InlineKeyboardButton("🚫 - الغاء واسترجاع الرصيد", callback_data=f"cancel_ord_{order_id}_{cost}"),
            telebot.types.InlineKeyboardButton("🔚 - العودة", callback_data="back_home")
        )
        
        try:
            bot.edit_message_text(success_text, call.message.chat.id, call.message.message_id, reply_markup=control_markup, parse_mode="Markdown")
        except:
            bot.send_message(call.message.chat.id, success_text, reply_markup=control_markup, parse_mode="Markdown")

    # --- فحص حالة الكود الحقيقي ---
    elif call.data.startswith("check_sms_"):
        order_id = call.data.split("_")[2]
        bot.answer_callback_query(call.id, "🔄 جاري فحص وصول الكود من السيرفر...")
        
        check_res = smspool_check_sms(order_id)
        if not check_res:
            bot.answer_callback_query(call.id, "⚠️ فشل الاتصال بالسيرفر، حاول مرة أخرى.", show_alert=True)
            return

        status_code = check_res.get("status")
        sms_code = check_res.get("sms") or check_res.get("code")
        phone_num = check_res.get("phonenumber", "متاح")

        if sms_code and sms_code != "null" and str(sms_code).strip() != "":
            complete_text = (
                f"🟥 **- تفاصيل الرقم:**\n\n"
                f"☎️ - الرقم: `+{phone_num}`\n"
                f"💬 - الكود: تم إرساله إليك بالأسفل.\n"
                f"🌀 - الحالة: مكتمل ✅\n"
                f"💰 - السعر: تم الخصم بنجاح\n\n"
                f"✅ تم وصول الكود بنجاح. 💨❤️"
            )
            bot.send_message(call.message.chat.id, f"✅ **كود التفعيل الحقيقي:** `{sms_code}`", parse_mode="Markdown")
            
            conn = sqlite3.connect("emperor_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT service_name, country_name, price FROM orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                send_to_channel(row[0], row[1], phone_num, row[2], user_id, str(sms_code))

            try:
                bot.edit_message_text(complete_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "⏳ لم يصل الكود بعد، انتظر قليلاً واضغط تحديث مجدداً.", show_alert=True)

    # --- إلغاء الطلب واسترجاع الرصيد ---
    elif call.data.startswith("cancel_ord_"):
        parts = call.data.split("_")
        order_id = parts[2]
        cost = float(parts[3])

        cancel_res = smspool_cancel_order(order_id)
        update_user_balance(user_id, cost)
        
        bot.answer_callback_query(call.id, "❌ تم إلغاء الطلب واسترجاع الرصيد إلى محفظتك بنجاح.", show_alert=True)
        send_welcome(call.message)

    # --- سجل الحساب ---
    elif call.data == "history":
        bot.answer_callback_query(call.id, "سجل الحساب")
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("📊 - إحصائيات الحساب ☑️", callback_data="hist_stats"),
            telebot.types.InlineKeyboardButton("📞 - قائمة الأرقام المكتملة", callback_data="hist_numbers"),
            telebot.types.InlineKeyboardButton("🔙 - رجوع", callback_data="back_home")
        )
        text = "☑️ **- اهلا فيك عزيزي في سجل الحساب ⬇️**\n\nاختر القسم الذي تريد استعراضه:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "hist_stats":
        balance, refs = get_user_data(user_id)
        text = f"📊 **إحصائيات حسابك:**\n\n💰 الرصيد الحالي: `{balance:.2f} ₽`\n👥 عدد الدعوات: `{refs}`\n🆔 معرف الحساب: `{user_id}`"
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("🔙 - رجوع للسجل", callback_data="history"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

    elif call.data == "hist_numbers":
        conn = sqlite3.connect("emperor_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT service_name, country_name, phone_number, price FROM orders WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        text = "📞 **سجل أرقامك:**\n\n"
        if rows:
            for r in rows:
                text += f"📱 {r[0]} | 🌍 {r[1]} | `+{r[2]}` | {r[3]} ₽\n"
        else:
            text += "لا توجد أرقام مسجلة حتى الآن."
            
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("🔙 - رجوع للسجل", callback_data="history"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

    # --- قسم اربح روبل (نظام الدعوات) ---
    elif call.data == "ref_section":
        bot.answer_callback_query(call.id, "قسم الأرباح")
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        _, refs = get_user_data(user_id)
        
        text = (
            f"✅ **- يمكنك من خلال هذه الميزة ربح نقاط عن طريق مشاركة رابط الدعوة مع الآخرين!**\n\n"
            f"☑️ **- رابط الدعوة الخاص بك:** `{ref_link}`\n\n"
            f"💰 **- أي شخص يقوم بالدخول عبر رابط الدعوة الخاص بك تحصل على 0.3 روبل.**\n\n"
            f"🔄 **- عدد فريقك الان : {refs} عضو** •🎈"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 رجوع", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # --- دعم ومساعدة ---
    elif call.data == "support":
        bot.answer_callback_query(call.id, "فتح قسم الدعم")
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("✔️ - التواصل مع الدعم اولاين", url=f"https://t.me/{DEVELOPER_USERNAME}"),
            telebot.types.InlineKeyboardButton("🔙 - الصفحة الرئيسية", callback_data="back_home")
        )
        text = "☑️ **- مرحبا بك في قسم طلب المساعدة ⬇️**"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # --- شحن الحساب ---
    elif call.data == "charge":
        balance, _ = get_user_data(user_id)
        m = telebot.types.InlineKeyboardMarkup()
        m.add(
            telebot.types.InlineKeyboardButton("💳 التواصل مع المؤسس للشحن", url=f"https://t.me/{DEVELOPER_USERNAME}"),
            telebot.types.InlineKeyboardButton("🔙 عودة", callback_data="back_home")
        )
        text = f"💻 **قسم شحن الرصيد الحقيقي** 💰\n\nرصيدك الحالي: `{balance:.2f} ₽`\nلشحن الحساب تواصل مع المطور مباشرة:"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

    # --- العودة للقائمة الرئيسية ---
    elif call.data == "back_home":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        send_welcome(call.message)

if __name__ == "__main__":
    # تشغيل سيرفر الويب الوهمي أولاً لإرضاء منصة Render
    keep_alive()
    print("Emperor Professional Bot is running successfully with Flask server...")
    # تشغيل البوت
    bot.infinity_polling(skip_pending=True)
