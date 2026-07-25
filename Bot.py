import os
import re
import time
import asyncio
from telethon import TelegramClient, events

# ---------------- CONFIGURATION ---------------- #

API_ID = 37661869
API_HASH = "9ea2a45a739b19c7fd3e5cf45a8b88c8"
SESSION_NAME = "telegram_session"
BOT_TOKEN = "8806195529:AAGUd-L5slC9B4VyAkWrY5B87_Kjko-MlLY"

user_states = {}

# ---------------- TELEGRAM LINK PARSER ---------------- #

def parse_telegram_link(link: str):
    threaded_pattern = r"t\.me/c/([0-9]+)/([0-9]+)/([0-9]+)"
    match_threaded = re.search(threaded_pattern, link)

    if match_threaded:
        channel_id = int(f"-100{match_threaded.group(1)}")
        message_id = int(match_threaded.group(3))
        return channel_id, message_id

    private_pattern = r"t\.me/c/([0-9]+)/([0-9]+)"
    match_private = re.search(private_pattern, link)

    if match_private:
        channel_id = int(f"-100{match_private.group(1)}")
        message_id = int(match_private.group(2))
        return channel_id, message_id

    public_pattern = r"t\.me/([a-zA-Z0-9_]+)/([0-9]+)"
    match_public = re.search(public_pattern, link)

    if match_public:
        channel = match_public.group(1)
        message_id = int(match_public.group(2))
        return channel, message_id

    return None, None


# ---------------- CLIENT INITIALIZATION ---------------- #

user_client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH,
    connection_retries=10,
    timeout=120,
    auto_reconnect=True,
    use_ipv6=False
)

bot = TelegramClient(
    "bot_session_id", 
    API_ID, 
    API_HASH,
    connection_retries=10,
    timeout=120
)

# ---------------- DOWNLOAD PROGRESS ---------------- #

async def download_media_with_progress(message, status_msg, media_type_name):
    download_path = "downloads/"

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    last_update_time = [0]
    last_bytes = [0]
    start_time = [time.time()]

    async def callback(current, total):
        current_time = time.time()

        if current_time - last_update_time[0] >= 1.5 or current == total:
            time_diff = current_time - start_time[0]
            speed = (current - last_bytes[0]) / time_diff if time_diff > 0 else 0

            last_update_time[0] = current_time
            last_bytes[0] = current
            start_time[0] = current_time

            percentage = (current / total) * 100 if total > 0 else 0
            downloaded_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024) if total > 0 else 0
            speed_mb = speed / (1024 * 1024)

            progress_text = (
                f"📥 **{media_type_name} ડાઉનલોડ ચાલુ છે...**\n\n"
                f"📊 પ્રગતિ: **{percentage:.2f}%**\n"
                f"💾 ડાઉનલોડ થયું: **{downloaded_mb:.2f} MB / {total_mb:.2f} MB**\n"
                f"⚡ સ્પીડ: **{speed_mb:.2f} MB/s**"
            )

            try:
                await status_msg.edit(progress_text)
            except Exception:
                pass

    try:
        # એરર લાવતી 'chunk_size' લાઇન અહીંથી કાઢી નાખી છે
        file_path = await message.download_media(
            file=download_path,
            progress_callback=callback
        )
        return file_path

    except Exception as e:
        print(f"[ERROR] Download Failed: {e}")
        return None


# ---------------- UPLOAD PROGRESS ---------------- #

async def upload_media_with_progress(
    chat_id,
    file_path,
    caption_text,
    status_msg,
    media_type_name
):
    last_update_time = [0]
    last_bytes = [0]
    start_time = [time.time()]

    async def callback(current, total):
        current_time = time.time()

        if current_time - last_update_time[0] >= 1.5 or current == total:
            time_diff = current_time - start_time[0]
            speed = (current - last_bytes[0]) / time_diff if time_diff > 0 else 0

            last_update_time[0] = current_time
            last_bytes[0] = current
            start_time[0] = current_time

            percentage = (current / total) * 100 if total > 0 else 0
            uploaded_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024) if total > 0 else 0
            speed_mb = speed / (1024 * 1024)

            progress_text = (
                f"📤 **{media_type_name} અપલોડ ચાલુ છે...**\n\n"
                f"📊 પ્રગતિ: **{percentage:.2f}%**\n"
                f"💾 અપલોડ થયું: **{uploaded_mb:.2f} MB / {total_mb:.2f} MB**\n"
                f"⚡ સ્પીડ: **{speed_mb:.2f} MB/s**"
            )

            try:
                await status_msg.edit(progress_text)
            except Exception:
                pass

    try:
        await bot.send_file(
            chat_id,
            file_path,
            caption=caption_text,
            supports_streaming=True,
            progress_callback=callback
        )

    except Exception as e:
        print(f"[ERROR] Upload Failed: {e}")


# ---------------- BOT COMMANDS & CHAT LOGIN ---------------- #

@bot.on(events.NewMessage(pattern="/start"))
async def start_command(event):
    await event.respond(
        "નમસ્તે! બોટ તૈયાર છે.\n"
        "પ્રાઇવેટ ચેનલમાંથી ડાઉનલોડ કરવા માટે `/login` કમાન્ડ મોકલો."
    )

@bot.on(events.NewMessage(pattern="/login"))
async def login_command(event):
    async with bot.conversation(event.chat_id, timeout=300) as conv:
        try:
            await conv.send_message("📱 તમારો મોબાઈલ નંબર દેશના કોડ સાથે મોકલો (દા.ત. `+919876543210`):")
            phone_msg = await conv.get_response()
            phone_number = phone_msg.text.strip()

            await user_client.connect()
            
            if not await user_client.is_user_authorized():
                await user_client.send_code_request(phone_number)
                
                await conv.send_message("📩 ટેલિગ્રામ પર આવેલો **OTP કોડ** અહીં મોકલો:")
                code_msg = await conv.get_response()
                code = code_msg.text.strip()

                try:
                    await user_client.sign_in(phone_number, code)
                except Exception as e:
                    if "SessionPasswordNeededError" in str(type(e)) or "password" in str(e).lower():
                        await conv.send_message("🔒 2-Step Verification Password મોકલો:")
                        pass_msg = await conv.get_response()
                        password = pass_msg.text.strip()
                        await user_client.sign_in(password=password)
                    else:
                        raise e

            await conv.send_message("✅ સફળતાપૂર્વક લોગિન થઈ ગયું છે! હવે લિંક મોકલો.")
        
        except asyncio.TimeoutError:
            await conv.send_message("⏱️ સમય મર્યાદા પૂરી થઈ ગઈ. `/login` ફરીથી મોકલો.")
        except Exception as e:
            await conv.send_message(f"❌ લોગિન એરર: {e}")


@bot.on(events.NewMessage(pattern="https://t.me/"))
async def handle_link(event):
    if not await user_client.is_user_authorized():
        await event.respond("⚠️ પહેલા `/login` કમાન્ડ મોકલીને લોગિન કરો!")
        return

    link = event.text.strip()
    channel, message_id = parse_telegram_link(link)

    if not channel or not message_id:
        await event.respond("❌ અયોગ્ય Telegram Link!")
        return

    user_states[event.sender_id] = {
        "channel": channel,
        "message_id": message_id
    }

    await event.respond("🔢 તમે કેટલા Message (Video/PDF) ફોરવર્ડ કરવા માંગો છો? માત્ર નંબર મોકલો:")


@bot.on(
    events.NewMessage(
        func=lambda e: (
            e.sender_id in user_states and e.text.isdigit()
        )
    )
)
async def handle_count(event):
    user_id = event.sender_id
    count = int(event.text.strip())

    data = user_states.pop(user_id)
    channel = data["channel"]
    start_message_id = data["message_id"]

    status_msg = await event.respond(f"⏳ કુલ {count} ફાઈલો પ્રક્રિયા થઈ રહી છે...")

    success_count = 0

    for i in range(count):
        current_msg_id = start_message_id + i

        try:
            await status_msg.edit(f"📥 ફાઈલ {i + 1}/{count} મેળવાઈ રહી છે...")

            message = await user_client.get_messages(
                channel,
                ids=current_msg_id
            )

            if not message:
                continue

            caption_text = message.text or message.caption or ""

            if message.video:
                file_path = await download_media_with_progress(
                    message,
                    status_msg,
                    "વીડિયો"
                )

                if file_path:
                    await upload_media_with_progress(
                        event.chat_id,
                        file_path,
                        caption_text,
                        status_msg,
                        "વીડિયો"
                    )

                    success_count += 1

                    if os.path.exists(file_path):
                        os.remove(file_path)

            elif message.document:
                file_path = await download_media_with_progress(
                    message,
                    status_msg,
                    "PDF/Document"
                )

                if file_path:
                    await upload_media_with_progress(
                        event.chat_id,
                        file_path,
                        caption_text,
                        status_msg,
                        "PDF/Document"
                    )

                    success_count += 1

                    if os.path.exists(file_path):
                        os.remove(file_path)

            else:
                print(f"[INFO] Message {current_msg_id} માં Video અથવા PDF નથી.")

        except Exception as e:
            print(f"[ERROR] Message {current_msg_id}: {e}")

    await status_msg.edit(
        f"🎉 પ્રક્રિયા સફળતાપૂર્વક પૂર્ણ!\n\n"
        f"કુલ {success_count}/{count} ફાઈલો મોકલાઈ ગઈ."
    )


# ---------------- MAIN ---------------- #

async def main():
    print("[INFO] ટેલિગ્રામ બોટ શરૂ થઈ રહ્યો છે...")
    await bot.start(bot_token=BOT_TOKEN)
    print("[INFO] Bot Live!")

    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
