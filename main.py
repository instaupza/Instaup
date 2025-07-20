    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageReactionUpdated
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, MessageReactionHandler, ChatMemberHandler
    import os, re, asyncio, logging, json
    import signal
    import sys
    import traceback
    from datetime import datetime, timedelta
    from typing import Dict, Any
    import pytz
    import time
    import threading

    # تنظیم لاگینگ پیشرفته
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")

    # متغیرهای جهانی برای مدیریت وضعیت
    is_running = True
    restart_count = 0
    max_restarts = 10

    # فایل ذخیره اطلاعات کاربران
    USER_DATA_FILE = "user_activity.json"
    #فایل ذخیره اطلاعات ری اکشن
    UNLIKED_REACTIONS_FILE = "unconfirmed_reactions.json"

    # فایل ذخیره کاربران تازه‌وارد
    NEW_USERS_FILE = "new_users.json"

    def load_unconfirmed_reactions():
        try:
            with open(UNLIKED_REACTIONS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def load_new_users():
        try:
            with open(NEW_USERS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_new_users(data):
        try:
            with open(NEW_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving new users data: {e}")

    def save_unconfirmed_reactions(data):
        try:
            with open(UNLIKED_REACTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving unconfirmed reactions data: {e}")

    # فایل لاگ‌ها
    LOG_FILE = "bot.log"

    # فایل ذخیره اطلاعات شب بخیر
    GOODNIGHT_DATA_FILE = "goodnight_clicks.json"

    # فایل ذخیره اطلاعات صبح بخیر
    GOODMORNING_DATA_FILE = "goodmorning_clicks.json"

    PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

    UNIT_SECONDS = {
        "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
        "ثانیه": 1, "ثانیه‌ها": 1, "ثانیهها": 1,
        "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
        "دقیقه": 60, "دقیقه‌ها": 60, "دقیقهها": 60,
        "h": 3600, "hour": 3600, "hours": 3600,
        "ساعت": 3600, "ساعتها": 3600,
        "d": 86400, "day": 86400, "days": 86400,
        "روز": 86400, "روزها": 86400,
        "w": 604800, "week": 604800, "weeks": 604800,
        "هفته": 604800, "هفته‌ها": 604800,
        "mo": 2592000, "month": 2592000, "months": 2592000,
        "ماه": 2592000, "ماه‌ها": 2592000,
        "y": 31536000, "year": 31536000, "years": 31536000,
        "سال": 31536000, "سال‌ها": 31536000,
    }

    DURATION_RE = re.compile(r"(\d+)\s*([A-Za-zآ-ی]+)")

    def load_user_data() -> Dict[str, Any]:
        """بارگذاری اطلاعات کاربران از فایل"""
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_user_data(data: Dict[str, Any]):
        """ذخیره اطلاعات کاربران در فایل"""
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_goodnight_data() -> Dict[str, Any]:
        """بارگذاری اطلاعات شب بخیر از فایل"""
        try:
            with open(GOODNIGHT_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_goodnight_data(data: Dict[str, Any]):
        """ذخیره اطلاعات شب بخیر در فایل"""
        with open(GOODNIGHT_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_goodmorning_data() -> Dict[str, Any]:
        """بارگذاری اطلاعات صبح بخیر از فایل"""
        try:
            with open(GOODMORNING_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_goodmorning_data(data: Dict[str, Any]):
        """ذخیره اطلاعات صبح بخیر در فایل"""
        with open(GOODMORNING_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # توابع مدیریت خطا و بازیابی
    def signal_handler(signum, frame):
        """مدیریت سیگنال‌های سیستم"""
        global is_running
        logging.info(f"Signal {signum} received. Shutting down gracefully...")
        is_running = False

    def save_bot_state():
        """ذخیره وضعیت فعلی ربات"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "restart_count": restart_count,
            "last_update": time.time()
        }
        try:
            with open("bot_state.json", 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving bot state: {e}")

    def load_bot_state():
        """بارگذاری وضعیت قبلی ربات"""
        global restart_count
        try:
            with open("bot_state.json", 'r', encoding='utf-8') as f:
                state = json.load(f)
                restart_count = state.get("restart_count", 0)
                logging.info(f"Bot state loaded. Previous restart count: {restart_count}")
                return state
        except FileNotFoundError:
            logging.info("No previous bot state found.")
            return {}
        except Exception as e:
            logging.error(f"Error loading bot state: {e}")
            return {}

    async def error_handler(update, context):
        """مدیریت خطاهای غیرمنتظره"""
        try:
            logging.error(f"Exception while handling an update: {context.error}")
            logging.error(f"Update: {update}")
            logging.error(traceback.format_exc())

            # فقط در لاگ ذخیره می‌شود، هیچ پیامی در گروه ارسال نمی‌شود
            add_log("error", f"Error occurred: {str(context.error)}", 
                    getattr(update.effective_user, 'id', None) if update else None,
                    getattr(update.effective_chat, 'id', None) if update else None)

        except Exception as e:
            logging.error(f"Error in error handler: {e}")

    def restart_bot():
        """راه‌اندازی مجدد ربات"""
        global restart_count
        restart_count += 1
        save_bot_state()

        logging.info(f"Restarting bot... (Attempt {restart_count}/{max_restarts})")

        if restart_count <= max_restarts:
            time.sleep(5)  # انتظار ۵ ثانیه قبل از راه‌اندازی مجدد
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            logging.critical("Maximum restart attempts reached. Bot will stay down.")
            sys.exit(1)

    def heartbeat_monitor():
        """نظارت بر وضعیت ربات"""
        last_heartbeat = time.time()

        def update_heartbeat():
            nonlocal last_heartbeat
            last_heartbeat = time.time()

        def check_heartbeat():
            while is_running:
                try:
                    current_time = time.time()
                    if current_time - last_heartbeat > 300:  # اگر بیش از ۵ دقیقه پاسخ نداد
                        logging.warning("Bot seems to be stuck. Initiating restart...")
                        restart_bot()
                    time.sleep(60)  # بررسی هر دقیقه
                except Exception as e:
                    logging.error(f"Error in heartbeat monitor: {e}")

        # شروع thread نظارت
        monitor_thread = threading.Thread(target=check_heartbeat, daemon=True)
        monitor_thread.start()

        return update_heartbeat

    async def keep_alive_ping(context):
        """پینگ دوره‌ای برای نگه داشتن ربات زنده"""
        try:
            await context.bot.get_me()
            logging.debug("Keep-alive ping successful")
        except Exception as e:
            logging.warning(f"Keep-alive ping failed: {e}")

    def update_user_activity(user_id: int, chat_id: int, username: str = None):
        """به‌روزرسانی آخرین فعالیت کاربر"""
        data = load_user_data()
        user_key = f"{chat_id}_{user_id}"

        data[user_key] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "username": username,
            "last_activity": datetime.now().isoformat(),
            "warned": False
        }

        save_user_data(data)

    async def check_inactive_users(context: ContextTypes.DEFAULT_TYPE):
        """بررسی کاربران غیرفعال و ارسال هشدار یا حذف"""
        try:
            data = load_user_data()
            now = datetime.now()
            updated = False

            for user_key, user_info in list(data.items()):
                try:
                    last_activity = datetime.fromisoformat(user_info["last_activity"])
                    days_inactive = (now - last_activity).days

                    chat_id = user_info["chat_id"]
                    user_id = user_info["user_id"]
                    username = user_info.get("username", "کاربر")

                    # بررسی اینکه کاربر ادمین است یا نه
                    try:
                        member = await context.bot.get_chat_member(chat_id, user_id)
                        if member.status in ['creator', 'administrator']:
                            # ادمین‌ها از بررسی غیرفعال بودن مستثنی هستند
                            continue
                    except:
                        pass

                    # اگر 3 روز غیرفعال بوده و هنوز هشدار نگرفته
                    if days_inactive >= 3 and not user_info.get("warned", False):
                        try:
                            mention = f"@{username}" if username else f"[کاربر](tg://user?id={user_id})"
                            warning_text = f"{mention} عزیزم شما سه روزه هیچ فعالیتی نداشتی و اگر تا 24 ساعت آینده هیچ فعالیتی نداشته باشی از گروه اخراج میشی"

                            await context.bot.send_message(chat_id=chat_id, text=warning_text, parse_mode='HTML')

                            # علامت‌گذاری به عنوان هشدار داده شده
                            data[user_key]["warned"] = True
                            updated = True

                            logging.info(f"Warning sent to user {user_id} in chat {chat_id}")

                        except Exception as e:
                            logging.error(f"Failed to send warning to user {user_id}: {e}")

                    # اگر 4 روز غیرفعال بوده (3 روز + 1 روز بعد از هشدار)
                    elif days_inactive >= 4 and user_info.get("warned", False):
                        try:
                            # حذف کاربر از گروه
                            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)

                            # حذف از دیتابیس
                            del data[user_key]
                            updated = True

                            logging.info(f"User {user_id} removed from chat {chat_id} due to inactivity")

                        except Exception as e:
                            logging.error(f"Failed to remove user {user_id}: {e}")

                except Exception as e:
                    logging.error(f"Error processing user {user_key}: {e}")

            if updated:
                save_user_data(data)

        except Exception as e:
            logging.error(f"Error in check_inactive_users: {e}")
            logging.error(traceback.format_exc())

    async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ردیابی فعالیت تمام کاربران در گروه"""
        if update.effective_chat.type in ['group', 'supergroup']:
            # اگر پیام از کانال ارسال شده، ردیابی نکن
            if update.message.sender_chat:
                return

            user = update.effective_user
            if user:
                update_user_activity(
                    user_id=user.id,
                    chat_id=update.effective_chat.id,
                    username=user.username
                )

    def fa_to_en(text: str) -> str:
        return text.translate(PERSIAN_DIGITS)

    def parse_duration(text: str) -> int:
        text = fa_to_en(text.lower())
        seconds = 0
        for amount, unit in DURATION_RE.findall(text):
            if unit in UNIT_SECONDS:
                seconds += int(amount) * UNIT_SECONDS[unit]
        return seconds

    def fmt_time(total: int) -> str:
        days, rem = divmod(total, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        return f"{days:02d}:{h:02d}:{m:02d}:{s:02d}" if days else f"{h:02d}:{m:02d}:{s:02d}"

    async def run_timer(bot, chat_id: int, message_id: int, total: int):
        remain = total
        while remain > 0:
            await asyncio.sleep(1)
            remain -= 1
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=fmt_time(remain))
            except Exception:
                pass
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="زمان پایان یافت ❌")
        except Exception:
            pass

    async def countdown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        txt = update.message.text
        if context.args:                           # /countdown ...
            query = " ".join(context.args)
        else:                                      # متن حاوی «تایم ...»
            idx = txt.find("تایم")
            query = txt[idx + len("تایم"):].strip() if idx != -1 else ""
        total = parse_duration(query)
        if total <= 0:
            return
        msg = await update.message.reply_text(fmt_time(total))
        context.application.create_task(
            run_timer(context.bot, update.effective_chat.id, msg.message_id, total)
        )

    async def activity_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار فعالیت کاربران (فقط برای ادمین‌ها)"""
        # تشخیص نوع update (پیام معمولی یا callback query)
        message = update.message if update.message else update.callback_query.message

        if update.effective_chat.type not in ['group', 'supergroup']:
            await message.reply_text("این دستور فقط در گروه‌ها کار می‌کند.")
            return

        # بررسی ادمین بودن
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
            if member.status not in ['creator', 'administrator']:
                await message.reply_text("فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")
                return
        except:
            return

        data = load_user_data()
        chat_id = update.effective_chat.id
        now = datetime.now()

        inactive_users = []
        warned_users = []

        for user_key, user_info in data.items():
            if user_info["chat_id"] == chat_id:
                last_activity = datetime.fromisoformat(user_info["last_activity"])
                days_inactive = (now - last_activity).days

                if days_inactive >= 3:
                    username = user_info.get("username", f"ID: {user_info['user_id']}")
                    if user_info.get("warned", False):
                        warned_users.append(f"⚠️ {username} ({days_inactive} روز)")
                    else:
                        inactive_users.append(f"🔴 {username} ({days_inactive} روز)")

        stats_text = "📊 آمار فعالیت کاربران:\n\n"

        if inactive_users:
            stats_text += "کاربران غیرفعال (بدون هشدار):\n"
            stats_text += "\n".join(inactive_users[:10])  # نمایش حداکثر 10 کاربر
            stats_text += "\n\n"

        if warned_users:
            stats_text += "کاربران هشدار داده شده:\n"
            stats_text += "\n".join(warned_users[:10])
            stats_text += "\n\n"

        if not inactive_users and not warned_users:
            stats_text += "آماری موجود نیست - همه کاربران فعال هستند!"

        await message.reply_text(stats_text)

    # -------------------------------- Logging Functions --------------------------------
    def add_log(log_type: str, description: str, user_id: int = None, chat_id: int = None):
        """ثبت یک رویداد (لاگ)"""
        now = datetime.now().isoformat()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            log_record = {
                "time": now,
                "type": log_type,
                "user_id": user_id,
                "chat_id": chat_id,
                "description": description
            }
            f.write(json.dumps(log_record, ensure_ascii=False) + "\n")

    def read_logs():
        """خواندن لاگ‌ها از فایل"""
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return [json.loads(line.strip()) for line in lines if line.strip()]
        except FileNotFoundError:
            return []

    def clean_old_logs(days=7):
        """
        پاک کردن لاگ‌های قدیمی‌تر از یک مدت معین.
        به صورت پیش‌فرض لاگ‌های قدیمی‌تر از ۷ روز پاک می‌شوند.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        all_logs = read_logs()
        valid_logs = [log for log in all_logs if datetime.fromisoformat(log["time"]) >= cutoff_date]
        # بازنویسی فایل لاگ با لاگ‌های معتبر
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for log in valid_logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        logging.info(f"Old logs (older than {days} days) cleaned up.")

    async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لاگ‌ها به صورت دسته‌بندی شده"""
        logs = read_logs()

        # تشخیص نوع update (پیام معمولی یا callback query)
        message = update.message if update.message else update.callback_query.message

        if not logs:
            await message.reply_text("هیچ لاگی وجود ندارد.")
            return

        log_text = "📜 آخرین رویدادها:\n"
        for log in logs[-10:]:  # نمایش ۱۰ لاگ آخری
            log_text += f"- {log['time']} - {log['type']}: {log['description']}\n"

        await message.reply_text(log_text)

    async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
        member = update.chat_member.new_chat_member
        if member.status == 'member':
            user_id = member.user.id
            chat_id = update.chat_member.chat.id
            new_users = load_new_users()
            key = f"{chat_id}_{user_id}"

            if key not in new_users:
                # همیشه کاربر رو به عنوان تازه‌وارد درنظر بگیر (حتی اگر قبلاً بوده)
                new_users[key] = {
                    "joined_at": datetime.now().isoformat(),
                    "reactions": []
                }
                save_new_users(new_users)

    # -------------------------------- Menu Functions --------------------------------
    async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منو با دکمه‌های inline"""
        keyboard = [
            [InlineKeyboardButton("نمایش لاگ‌ها", callback_data='show_logs')],
            [InlineKeyboardButton("آمار فعالیت", callback_data='activity_stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("منو:", reply_markup=reply_markup)

    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دکمه‌های inline"""
        query = update.callback_query
        await query.answer()  # تایید دریافت کوئری

        if query.data == 'show_logs':
            await show_logs(update, context)
        elif query.data == 'activity_stats':
            await activity_stats_cmd(update, context)
        elif query.data.startswith('liked_'):
            # پردازش تأیید لایک
            parts = query.data.split('_')
            if len(parts) >= 3:
                user_id = int(parts[1])
                original_message_id = int(parts[2])
                await handle_like_confirmation(update, context, user_id, original_message_id)
        elif query.data.startswith('goodnight_'):
            # پردازش کلیک شب بخیر
            await handle_goodnight_click(update, context)
        elif query.data.startswith('goodmorning_'):
            # پردازش کلیک صبح بخیر
            await handle_goodmorning_click(update, context)

    async def validate_instagram_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بررسی و مدیریت لینک‌های اینستاگرام"""
        if update.effective_chat.type not in ['group', 'supergroup']:
            return

        # اگر پیام از کانال ارسال شده باشد، کنترل نکن
        if update.message.sender_chat:
            return

        text = update.message.text
        user = update.effective_user
        new_users = load_new_users()
        key = f"{update.effective_chat.id}_{user.id}"

        if key in new_users:
            reaction_count = len(new_users[key]["reactions"])
            if reaction_count < 3:
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"عزیزم شما قبل از اینکه لینک بزاری باید حداقل ۳ لینک بالایی رو حمایت کنی و بهشون ری‌اکشن بزنی ❤️\n"
                             f"الان فقط {reaction_count}/3 انجام دادی.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logging.error(f"Error blocking new user link: {e}")
                return

        reactions = load_unconfirmed_reactions()
        key = f"{update.effective_chat.id}_{user.id}"

        if key in reactions and reactions[key].get("pending", False):
            reactions[key]["count"] += 1
            pending_count = reactions[key]["count"]

            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
            warn_msg = f"{mention} ❗️اخطار {pending_count}/3: شما به پست دیگران ری‌اکشن دادی ولی دکمه لایک نزدی و خودت لینک گذاشتی. در صورت تکرار حذف می‌شی."

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=warn_msg,
                parse_mode='HTML'
            )

            if pending_count >= 3:
                try:
                    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
                    await context.bot.unban_chat_member(update.effective_chat.id, user.id)
                    del reactions[key]
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"<a href='tg://user?id={user.id}'>{user.first_name}</a> به دلیل عدم رعایت قوانین از گروه حذف شد.",
                        parse_mode='HTML'
                    )
                except:
                    pass

            save_unconfirmed_reactions(reactions)

        # بررسی اینکه کاربر ادمین است یا نه
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
            if member.status in ['creator', 'administrator']:
                # ادمین‌ها از محدودیت‌ها مستثنی هستند
                return
        except:
            pass

        # اگر متن شامل لینک است
        if contains_any_link(text):
            # اگر لینک اینستاگرام معتبر نیست
            if not is_valid_instagram_link(text):
                try:
                    # حذف پیام
                    await update.message.delete()

                    # ارسال اخطار با تگ کردن کاربر
                    mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
                    warning_text = f"{mention} عزیزم اینجا فقط می‌تونی لینک پست، ریلز یا استوری اینستاگرام بذاری. لطفاً دقت کن ❤️"

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=warning_text,
                        parse_mode='HTML'
                    )

                    add_log("invalid_link", f"لینک نامعتبر حذف شد: {text[:50]}...", user.id, update.effective_chat.id)
                    return

                except Exception as e:
                    pass

    def is_valid_instagram_link(text: str) -> bool:
        """بررسی اینکه آیا متن شامل لینک معتبر اینستاگرام است"""
        # الگوهای لینک‌های مجاز اینستاگرام
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[A-Za-z0-9_-]+/?',  # پست
            r'https?://(?:www\.)?instagram\.com/reel/[A-Za-z0-9_-]+/?',  # ریلز
            r'https?://(?:www\.)?instagram\.com/stories/[A-Za-z0-9_.]+/\d+/?',  # استوری
            r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/p/[A-Za-z0-9_-]+/?',  # پست کاربر
            r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/reel/[A-Za-z0-9_-]+/?',  # ریلز کاربر
        ]

        # بررسی وجود لینک اینستاگرام معتبر
        for pattern in instagram_patterns:
            if re.search(pattern, text):
                return True

        return False

    def contains_any_link(text: str) -> bool:
        """بررسی وجود هر نوع لینک در متن"""
        link_pattern = r'https?://[^\s]+'
        return bool(re.search(link_pattern, text))

    async def handle_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت ری‌اکشن‌ها روی پیام‌های حاوی لینک"""
        try:
            # بررسی نوع آپدیت
            if hasattr(update, 'message_reaction') and update.message_reaction:
                reaction_update = update.message_reaction
            else:
                return

            user = reaction_update.user
            chat_id = reaction_update.chat.id
            message_id = reaction_update.message_id

            # بررسی اینکه کاربر واقعی است (نه ربات)
            if not user or user.is_bot:
                return

            # بررسی اینکه ری‌اکشن جدید اضافه شده
            new_reactions = reaction_update.new_reaction
            if not new_reactions:
                return

            # تگ کردن کاربر
            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            # ایجاد دکمه با تایمر
            keyboard = [[InlineKeyboardButton("آره لایک کردم ❤️ (30)", callback_data=f'liked_{user.id}_{message_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ارسال پیام سوال
            question_text = f"{mention} عزیزم شما به این پست ری‌اکشن زدی، آیا پست رو لایک کردی؟"

            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=question_text,
                reply_to_message_id=message_id,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            # ذخیره اطلاعات پیام برای استفاده در callback
            if not hasattr(context, 'chat_data'):
                context.chat_data = {}
            context.chat_data[f'reaction_question_{user.id}_{message_id}'] = {
                'question_message_id': sent_message.message_id,
                'original_message_id': message_id,
                'user_id': user.id,
                'chat_id': chat_id
            }

            # شروع تایمر برای پیام سوال
            context.application.create_task(
                question_timer_task(context, chat_id, sent_message.message_id, user.id, message_id)
            )

            # ذخیره‌سازی ری‌اکشن تاییدنشده
            reactions = load_unconfirmed_reactions()
            key = f"{chat_id}_{user.id}"
            if key not in reactions:
                reactions[key] = {"count": 0, "pending": True}
            else:
                reactions[key]["pending"] = True
            save_unconfirmed_reactions(reactions)

            add_log("reaction_detected", f"کاربر {user.username or user.first_name} به لینک ری‌اکشن زد", user.id, chat_id)

        except Exception as e:
            logging.error(f"Error handling reaction: {e}")

    async def question_timer_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int, question_message_id: int, user_id: int, original_message_id: int):
        """تایمر برای پیام سوال لایک"""
        data_key = f'reaction_question_{user_id}_{original_message_id}'

        # شمارش معکوس 30 ثانیه
        for remaining in range(30, 0, -1):
            try:
                # بررسی اینکه آیا پیام هنوز موجود است
                if not hasattr(context, 'chat_data') or data_key not in context.chat_data:
                    logging.info(f"Timer stopped - question already answered: {data_key}")
                    return  # پیام قبلاً پاسخ داده شده یا حذف شده

                # بروزرسانی دکمه با شمارش معکوس
                keyboard = [[InlineKeyboardButton(f"آره لایک کردم ❤️ ({remaining})", callback_data=f'liked_{user_id}_{original_message_id}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                try:
                    await context.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=question_message_id,
                        reply_markup=reply_markup
                    )
                    logging.debug(f"Timer updated: {remaining} seconds remaining")
                except Exception as edit_error:
                    if "message is not modified" not in str(edit_error) and "message to edit not found" not in str(edit_error):
                        logging.error(f"Error updating timer button: {edit_error}")
                    # اگر پیام پیدا نشد، تایمر را متوقف کن
                    if "message to edit not found" in str(edit_error):
                        logging.info("Timer stopped - message not found")
                        return

                # انتظار 1 ثانیه
                await asyncio.sleep(1)

            except Exception as e:
                logging.error(f"Error in timer loop: {e}")
                break

        # پس از پایان تایمر، پیام سوال را حذف کن
        try:
            # بررسی مجدد وجود داده
            if hasattr(context, 'chat_data') and data_key in context.chat_data:
                logging.info(f"Timer expired, deleting question message: {question_message_id}")

                # حذف پیام سوال
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=question_message_id)
                    logging.info(f"Question message deleted successfully: {question_message_id}")
                except Exception as delete_error:
                    logging.error(f"Error deleting question message: {delete_error}")

                # ارسال پیام اخطار
                user_mention = f"<a href='tg://user?id={user_id}'>کاربر</a>"
                warning_text = f"{user_mention} بخاطر بی اعتنایی به حقوق دیگران و ری اکشن بی توجه با ارسال لینک بعدی یک اخطار دریافت خواهید کرد"

                try:
                    warning_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=warning_text,
                        parse_mode='HTML'
                    )
                    logging.info(f"Warning message sent: {warning_message.message_id}")

                    # تنظیم تایمر برای حذف پیام اخطار پس از 1 دقیقه
                    context.application.create_task(
                        delete_message_after_delay(context, chat_id, warning_message.message_id, 60)
                    )

                except Exception as warning_error:
                    logging.error(f"Error sending warning message: {warning_error}")

                # حذف اطلاعات ذخیره شده
                try:
                    del context.chat_data[data_key]
                    logging.info(f"Timer data cleaned up: {data_key}")
                except Exception as cleanup_error:
                    logging.error(f"Error cleaning up timer data: {cleanup_error}")
            else:
                logging.info(f"Timer data not found or already cleaned: {data_key}")

        except Exception as e:
            logging.error(f"Error in question timer task cleanup: {e}")

    async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
        """حذف پیام پس از مدت زمان مشخص"""
        try:
            logging.info(f"Starting delayed deletion for message {message_id} in {delay} seconds")
            await asyncio.sleep(delay)

            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logging.info(f"Message {message_id} deleted successfully after {delay} seconds")

        except Exception as e:
            if "message to delete not found" in str(e):
                logging.info(f"Message {message_id} already deleted or not found")
            else:
                logging.error(f"Error deleting message {message_id}: {e}")

    async def handle_like_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, original_message_id: int):
        """مدیریت تأیید لایک کردن"""
        query = update.callback_query
        chat_id = query.message.chat.id

        # دریافت اطلاعات ذخیره شده
        data_key = f'reaction_question_{user_id}_{original_message_id}'
        stored_data = context.chat_data.get(data_key, {})

        logging.info(f"Like confirmation received for user {user_id}, message {original_message_id}")

        # حذف پیام سوال
        question_message_id = stored_data.get('question_message_id') or query.message.message_id
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=question_message_id)
            logging.info(f"Question message deleted: {question_message_id}")
        except Exception as e:
            logging.error(f"Error deleting question message: {e}")

        # حذف اطلاعات تایمر برای متوقف کردن آن
        if data_key in context.chat_data:
            del context.chat_data[data_key]
            logging.info(f"Timer data removed: {data_key}")

        # ارسال پیام تأیید
        user = query.from_user
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

        confirmation_text = f"✅ کاربر {mention} پست رو حمایت کرد و لایک زد"

        confirmation_message = await context.bot.send_message(
            chat_id=chat_id,
            text=confirmation_text,
            reply_to_message_id=original_message_id,
            parse_mode='HTML'
        )

        # تنظیم تایمر برای حذف پیام تأیید پس از 3 دقیقه
        context.application.create_task(
            delete_message_after_delay(context, chat_id, confirmation_message.message_id, 60)
        )

        # به‌روزرسانی وضعیت ری‌اکشن
        reactions = load_unconfirmed_reactions()
        key = f"{chat_id}_{user.id}"
        if key in reactions:
            reactions[key]["pending"] = False
            reactions[key]["count"] = 0  # ریست کردن شمارنده
            save_unconfirmed_reactions(reactions)

            # اگر کاربر تازه‌وارد بود، این پیام را به لیست حمایت‌ها اضافه کن
            new_users = load_new_users()
            new_key = f"{chat_id}_{user.id}"
            if new_key in new_users:
                if original_message_id not in new_users[new_key]["reactions"]:
                    new_users[new_key]["reactions"].append(original_message_id)

                    # اگر تعداد حمایت‌ها به ۳ رسید، کاربر را از لیست حذف کن
                    if len(new_users[new_key]["reactions"]) >= 3:
                        del new_users[new_key]
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🎉 {mention} عزیز حالا می‌تونی آزادانه لینک بذاری!",
                            parse_mode='HTML'
                        )
                    save_new_users(new_users)

        # حذف اطلاعات ذخیره شده
        if data_key in context.chat_data:
            del context.chat_data[data_key]

        add_log("like_confirmed", f"کاربر {user.username or user.first_name} لایک خود را تأیید کرد", user.id, chat_id)

        await query.answer("✅ تأیید شد! ممنون از حمایتت 😘")

    async def send_goodnight_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """ارسال پیام شب بخیر با دکمه تعاملی"""
        goodnight_text = "عزیزان من بیدارم تا حواسم باشه شما راحت بخوابین 😘 شبتون بخیر"

        # ایجاد دکمه شیشه‌ای
        keyboard = [[InlineKeyboardButton("شب بخیر👋 (0)", callback_data=f'goodnight_{chat_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=goodnight_text,
                reply_markup=reply_markup
            )

            # ذخیره اطلاعات پیام شب بخیر
            goodnight_data = load_goodnight_data()
            message_key = f"{chat_id}_{message.message_id}"
            goodnight_data[message_key] = {
                "chat_id": chat_id,
                "message_id": message.message_id,
                "clicked_users": [],
                "created_at": datetime.now().isoformat()
            }
            save_goodnight_data(goodnight_data)

            add_log("goodnight_sent", f"پیام شب بخیر ارسال شد", chat_id=chat_id)

        except Exception as e:
            logging.error(f"Error sending goodnight message: {e}")

    async def handle_goodnight_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کلیک روی دکمه شب بخیر"""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat.id
        message_id = query.message.message_id

        # بارگذاری اطلاعات شب بخیر
        goodnight_data = load_goodnight_data()
        message_key = f"{chat_id}_{message_id}"

        if message_key not in goodnight_data:
            await query.answer("خطا در پردازش درخواست")
            return

        message_data = goodnight_data[message_key]
        clicked_users = message_data.get("clicked_users", [])

        # بررسی اینکه کاربر قبلاً کلیک کرده یا نه
        if user.id in clicked_users:
            # هیچ پیامی نمایش نمی‌دهیم، فقط پاسخ می‌دهیم
            await query.answer()
            return

        # اضافه کردن کاربر به لیست کلیک کردگان
        clicked_users.append(user.id)
        message_data["clicked_users"] = clicked_users
        goodnight_data[message_key] = message_data
        save_goodnight_data(goodnight_data)

        # به‌روزرسانی دکمه با تعداد جدید
        count = len(clicked_users)
        new_keyboard = [[InlineKeyboardButton(f"شب بخیر👋 ({count})", callback_data=f'goodnight_{chat_id}')]]
        new_reply_markup = InlineKeyboardMarkup(new_keyboard)

        try:
            await query.edit_message_reply_markup(reply_markup=new_reply_markup)
            await query.answer("شب بخیر عزیزم! 😘")

            add_log("goodnight_click", f"کاربر {user.username or user.first_name} شب بخیر گفت", user.id, chat_id)

        except Exception as e:
            logging.error(f"Error updating goodnight button: {e}")
            await query.answer("شب بخیر عزیزم! 😘")

    async def send_goodmorning_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """ارسال پیام صبح بخیر با دکمه تعاملی"""
        goodmorning_text = "صبح همگی بخیر،امیدوارم امروز یکی از پست هاتون وایرال بشه و ما افتخار کنیم😘"

        # ایجاد دکمه شیشه‌ای
        keyboard = [[InlineKeyboardButton("صبح بخیر ♥️ (0)", callback_data=f'goodmorning_{chat_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=goodmorning_text,
                reply_markup=reply_markup
            )

            # ذخیره اطلاعات پیام صبح بخیر
            goodmorning_data = load_goodmorning_data()
            message_key = f"{chat_id}_{message.message_id}"
            goodmorning_data[message_key] = {
                "chat_id": chat_id,
                "message_id": message.message_id,
                "clicked_users": [],
                "created_at": datetime.now().isoformat()
            }
            save_goodmorning_data(goodmorning_data)

            add_log("goodmorning_sent", f"پیام صبح بخیر ارسال شد", chat_id=chat_id)

        except Exception as e:
            logging.error(f"Error sending goodmorning message: {e}")

    async def handle_goodmorning_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کلیک روی دکمه صبح بخیر"""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat.id
        message_id = query.message.message_id

        # بارگذاری اطلاعات صبح بخیر
        goodmorning_data = load_goodmorning_data()
        message_key = f"{chat_id}_{message_id}"

        if message_key not in goodmorning_data:
            await query.answer("خطا در پردازش درخواست")
            return

        message_data = goodmorning_data[message_key]
        clicked_users = message_data.get("clicked_users", [])

        # بررسی اینکه کاربر قبلاً کلیک کرده یا نه
        if user.id in clicked_users:
            # هیچ پیامی نمایش نمی‌دهیم، فقط پاسخ می‌دهیم
            await query.answer()
            return

        # اضافه کردن کاربر به لیست کلیک کردگان
        clicked_users.append(user.id)
        message_data["clicked_users"] = clicked_users
        goodmorning_data[message_key] = message_data
        save_goodmorning_data(goodmorning_data)

        # به‌روزرسانی دکمه با تعداد جدید
        count = len(clicked_users)
        new_keyboard = [[InlineKeyboardButton(f"صبح بخیر ♥️ ({count})", callback_data=f'goodmorning_{chat_id}')]]
        new_reply_markup = InlineKeyboardMarkup(new_keyboard)

        try:
            await query.edit_message_reply_markup(reply_markup=new_reply_markup)
            await query.answer("صبح بخیر عزیزم! ♥️")

            add_log("goodmorning_click", f"کاربر {user.username or user.first_name} صبح بخیر گفت", user.id, chat_id)

        except Exception as e:
            logging.error(f"Error updating goodmorning button: {e}")
            await query.answer("صبح بخیر عزیزم! ♥️")

    async def scheduled_goodmorning_message(context: ContextTypes.DEFAULT_TYPE):
        """ارسال خودکار پیام صبح بخیر در ساعت 7:30"""
        # دریافت همه گروه‌هایی که ربات در آن‌ها عضو است
        data = load_user_data()
        chat_ids = set()

        for user_key, user_info in data.items():
            chat_ids.add(user_info["chat_id"])

        # ارسال پیام صبح بخیر به همه گروه‌ها
        for chat_id in chat_ids:
            await send_goodmorning_message(context, chat_id)

    async def scheduled_goodnight_message(context: ContextTypes.DEFAULT_TYPE):
        """ارسال خودکار پیام شب بخیر در ساعت 24"""
        # دریافت همه گروه‌هایی که ربات در آن‌ها عضو است
        data = load_user_data()
        chat_ids = set()

        for user_key, user_info in data.items():
            chat_ids.add(user_info["chat_id"])

        # ارسال پیام شب بخیر به همه گروه‌ها
        for chat_id in chat_ids:
            await send_goodnight_message(context, chat_id)

    async def handle_goodnight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دستور شب بخیر توسط ادمین"""
        if update.effective_chat.type not in ['group', 'supergroup']:
            return

        # بررسی اینکه کاربر ادمین است یا نه
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
            if member.status not in ['creator', 'administrator']:
                return
        except:
            return

        # ارسال پیام شب بخیر
        await send_goodnight_message(context, update.effective_chat.id)

    async def handle_goodmorning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دستور صبح بخیر توسط ادمین"""
        if update.effective_chat.type not in ['group', 'supergroup']:
            return

        # بررسی اینکه کاربر ادمین است یا نه
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
            if member.status not in ['creator', 'administrator']:
                return
        except:
            return

        # ارسال پیام صبح بخیر
        await send_goodmorning_message(context, update.effective_chat.id)

    def main():
        global is_running

        # تنظیم signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # بارگذاری وضعیت قبلی
        load_bot_state()

        # شروع نظارت heartbeat
        update_heartbeat = heartbeat_monitor()

        try:
            # تنظیمات پیشرفته برای اتصال
            app = ApplicationBuilder().token(TOKEN).connection_pool_size(16).pool_timeout(30).read_timeout(20).write_timeout(20).connect_timeout(20).build()

            # اضافه کردن error handler
            app.add_error_handler(error_handler)

            # دستورات اصلی
            app.add_handler(CommandHandler("countdown", countdown_cmd))
            app.add_handler(CommandHandler("activity", activity_stats_cmd))
            app.add_handler(CommandHandler("menu", menu_cmd))

            # مدیریت دکمه‌های inline
            app.add_handler(CallbackQueryHandler(button_handler))

            # مدیریت ری‌اکشن‌ها - فعال شده
            app.add_handler(MessageReactionHandler(handle_message_reaction))

            # بررسی لینک‌های اینستاگرام (اولویت بالا)
            app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, validate_instagram_links), group=0)

            # ردیابی فعالیت تمام پیام‌ها در گروه‌ها
            app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, track_activity), group=1)
            app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"تایم"), countdown_cmd), group=2)

            # مدیریت دستور شب بخیر
            app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"شب بخیر") & filters.ChatType.GROUPS, handle_goodnight_command), group=0)

            # مدیریت دستور صبح بخیر
            app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"صبح بخیر") & filters.ChatType.GROUPS, handle_goodmorning_command), group=0)

            # هندلر برای ثبت ورود کاربران جدید
            app.add_handler(ChatMemberHandler(handle_new_member, ChatMemberHandler.CHAT_MEMBER))

            # تنظیم job برای بررسی دوره‌ای کاربران غیرفعال (هر 12 ساعت)
            if app.job_queue:
                app.job_queue.run_repeating(check_inactive_users, interval=43200, first=10)  # 43200 ثانیه = 12 ساعت
                # پاکسازی لاگ‌های قدیمی هر 24 ساعت
                async def clean_logs_job(context):
                    clean_old_logs()
                app.job_queue.run_repeating(clean_logs_job, interval=86400, first=60)  # 86400 ثانیه = 24 ساعت

                # تنظیم job برای ارسال پیام شب بخیر هر شب ساعت 24 به وقت تهران
                tehran_tz = pytz.timezone('Asia/Tehran')

                # محاسبه زمان 24:00 امشب به وقت تهران
                now_tehran = datetime.now(tehran_tz)
                midnight_tehran = now_tehran.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

                # تبدیل به UTC برای job queue
                midnight_utc = midnight_tehran.astimezone(pytz.UTC)

                # تنظیم job برای ارسال پیام شب بخیر هر شب ساعت 24 تهران
                app.job_queue.run_daily(scheduled_goodnight_message, time=midnight_utc.time())

                # محاسبه زمان 7:30 صبح فردا به وقت تهران
                morning_tehran = now_tehran.replace(hour=7, minute=30, second=0, microsecond=0)
                if morning_tehran <= now_tehran:
                    morning_tehran += timedelta(days=1)

                # تبدیل به UTC برای job queue
                morning_utc = morning_tehran.astimezone(pytz.UTC)

                # تنظیم job برای ارسال پیام صبح بخیر هر روز ساعت 7:30 تهران
                app.job_queue.run_daily(scheduled_goodmorning_message, time=morning_utc.time())

                # تنظیم job برای keep-alive ping هر ۳۰ ثانیه
                app.job_queue.run_repeating(keep_alive_ping, interval=30, first=10)

            print("Bot is running with enhanced stability and error recovery...")
            logging.info(f"Bot starting... (Restart count: {restart_count})")

            # شروع polling با تنظیمات بهینه
            while is_running:
                try:
                    save_bot_state()
                    app.run_polling(
                        allowed_updates=["message", "callback_query", "chat_member", "message_reaction"],
                        drop_pending_updates=True,
                        poll_interval=1.0,
                        timeout=10,
                        bootstrap_retries=5,
                        read_timeout=20,
                        write_timeout=20,
                        connect_timeout=20,
                        pool_timeout=20
                    )
                    break  # اگر polling به صورت عادی تمام شد

                except Exception as e:
                    logging.error(f"Polling error: {e}")
                    logging.error(traceback.format_exc())

                    if is_running:
                        logging.info("Attempting to restart polling in 10 seconds...")
                        time.sleep(10)
                        update_heartbeat()
                    else:
                        break

        except Exception as e:
            logging.critical(f"Critical error in main: {e}")
            logging.critical(traceback.format_exc())

            if is_running:
                restart_bot()
            else:
                sys.exit(1)

        finally:
            logging.info("Bot shutdown complete.")
            save_bot_state()

    if __name__ == "__main__":
        try:
            main()
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
            is_running = False
        except Exception as e:
            logging.critical(f"Unhandled exception: {e}")
            logging.critical(traceback.format_exc())
            restart_bot()    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    # بررسی اینکه کاربر ادمین است یا نه
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ['creator', 'administrator']:
            return
    except:
        return

    # ارسال پیام صبح بخیر
    await send_goodmorning_message(context, update.effective_chat.id)

def main():
    global is_running

    # تنظیم signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # بارگذاری وضعیت قبلی
    load_bot_state()

    # شروع نظارت heartbeat
    update_heartbeat = heartbeat_monitor()

    try:
        # تنظیمات پیشرفته برای اتصال
        app = ApplicationBuilder().token(TOKEN).connection_pool_size(16).pool_timeout(30).read_timeout(20).write_timeout(20).connect_timeout(20).build()

        # اضافه کردن error handler
        app.add_error_handler(error_handler)

        # دستورات اصلی
        app.add_handler(CommandHandler("countdown", countdown_cmd))
        app.add_handler(CommandHandler("activity", activity_stats_cmd))
        app.add_handler(CommandHandler("menu", menu_cmd))

        # مدیریت دکمه‌های inline
        app.add_handler(CallbackQueryHandler(button_handler))

        # مدیریت ری‌اکشن‌ها - فعال شده
        app.add_handler(MessageReactionHandler(handle_message_reaction))

        # بررسی لینک‌های اینستاگرام (اولویت بالا)
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, validate_instagram_links), group=0)

        # ردیابی فعالیت تمام پیام‌ها در گروه‌ها
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, track_activity), group=1)
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"تایم"), countdown_cmd), group=2)

        # مدیریت دستور شب بخیر
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"شب بخیر") & filters.ChatType.GROUPS, handle_goodnight_command), group=0)

        # مدیریت دستور صبح بخیر
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"صبح بخیر") & filters.ChatType.GROUPS, handle_goodmorning_command), group=0)

        # هندلر برای ثبت ورود کاربران جدید
        app.add_handler(ChatMemberHandler(handle_new_member, ChatMemberHandler.CHAT_MEMBER))

        # تنظیم job برای بررسی دوره‌ای کاربران غیرفعال (هر 12 ساعت)
        if app.job_queue:
            app.job_queue.run_repeating(check_inactive_users, interval=43200, first=10)  # 43200 ثانیه = 12 ساعت
            # پاکسازی لاگ‌های قدیمی هر 24 ساعت
            async def clean_logs_job(context):
                clean_old_logs()
            app.job_queue.run_repeating(clean_logs_job, interval=86400, first=60)  # 86400 ثانیه = 24 ساعت

            # تنظیم job برای ارسال پیام شب بخیر هر شب ساعت 24 به وقت تهران
            tehran_tz = pytz.timezone('Asia/Tehran')

            # محاسبه زمان 24:00 امشب به وقت تهران
            now_tehran = datetime.now(tehran_tz)
            midnight_tehran = now_tehran.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

            # تبدیل به UTC برای job queue
            midnight_utc = midnight_tehran.astimezone(pytz.UTC)

            # تنظیم job برای ارسال پیام شب بخیر هر شب ساعت 24 تهران
            app.job_queue.run_daily(scheduled_goodnight_message, time=midnight_utc.time())

            # محاسبه زمان 7:30 صبح فردا به وقت تهران
            morning_tehran = now_tehran.replace(hour=7, minute=30, second=0, microsecond=0)
            if morning_tehran <= now_tehran:
                morning_tehran += timedelta(days=1)

            # تبدیل به UTC برای job queue
            morning_utc = morning_tehran.astimezone(pytz.UTC)

            # تنظیم job برای ارسال پیام صبح بخیر هر روز ساعت 7:30 تهران
            app.job_queue.run_daily(scheduled_goodmorning_message, time=morning_utc.time())

            # تنظیم job برای keep-alive ping هر ۳۰ ثانیه
            app.job_queue.run_repeating(keep_alive_ping, interval=30, first=10)

        print("Bot is running with enhanced stability and error recovery...")
        logging.info(f"Bot starting... (Restart count: {restart_count})")

        # شروع polling با تنظیمات بهینه
        while is_running:
            try:
                save_bot_state()
                app.run_polling(
                    allowed_updates=["message", "callback_query", "chat_member", "message_reaction"],
                    drop_pending_updates=True,
                    poll_interval=1.0,
                    timeout=10,
                    bootstrap_retries=5,
                    read_timeout=20,
                    write_timeout=20,
                    connect_timeout=20,
                    pool_timeout=20
                )
                break  # اگر polling به صورت عادی تمام شد

            except Exception as e:
                logging.error(f"Polling error: {e}")
                logging.error(traceback.format_exc())

                if is_running:
                    logging.info("Attempting to restart polling in 10 seconds...")
                    time.sleep(10)
                    update_heartbeat()
                else:
                    break

    except Exception as e:
        logging.critical(f"Critical error in main: {e}")
        logging.critical(traceback.format_exc())

        if is_running:
            restart_bot()
        else:
            sys.exit(1)

    finally:
        logging.info("Bot shutdown complete.")
        save_bot_state()
from keep_alive import keep_alive

if __name__ == "__main__":
    keep_alive()
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
        is_running = False
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        logging.critical(traceback.format_exc())
        restart_bot()