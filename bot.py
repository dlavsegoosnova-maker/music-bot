import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from yt_dlp import YoutubeDL

# Токен берется из настроек окружения или вставляется сюда
TOKEN = os.getenv("BOT_TOKEN", "9081136516:AAEPLoKpm15KgA7KXw7GT5TlLNRVBxyIapA")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_results = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет. Напиши название песни.")

@dp.message(F.text)
async def search_music(message: types.Message):
    query = message.text
    msg = await message.answer("🔎 Ищу...")

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'default_search': 'ytsearch5', # Ищем 5 вариантов
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [])

        if not entries:
            await msg.edit_text("Ничего не найдено 😔")
            return

        user_id = message.from_user.id
        search_results[user_id] = entries

        buttons = []
        for idx, entry in enumerate(entries):
            title = entry.get('title', 'Без названия')[:40]
            buttons.append([types.InlineKeyboardButton(text=title, callback_data=f"dl_{idx}")])

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        await msg.edit_text(f"🎵 Результаты для: *{query}*", reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text("Ошибка поиска.")

@dp.callback_query(F.data.startswith("dl_"))
async def download_track(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    if user_id not in search_results or idx >= len(search_results[user_id]):
        await callback.answer("Кнопка устарела!", show_alert=True)
        return

    track_info = search_results[user_id][idx]
    video_url = track_info.get('url') or f"https://www.youtube.com/watch?v={track_info.get('id')}"
    
    await callback.answer("⏳ Скачиваю...")
    status_msg = await callback.message.answer("⬇️ Загружаю аудио...")

    filename = f"track_{user_id}_{idx}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{filename}.%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'quiet': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        mp3_file = f"{filename}.mp3"
        audio = types.FSInputFile(mp3_file)
        
        await callback.message.answer_audio(audio, title=track_info.get('title'))
        await status_msg.delete()

        if os.path.exists(mp3_file):
            os.remove(mp3_file)

    except Exception as e:
        await status_msg.edit_text("Не удалось скачать трек.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
