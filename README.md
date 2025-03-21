# Video Downloader Telegram Bot

Telegram бот для скачивания видео из:
- Instagram Reels
- TikTok
- YouTube Shorts

## Возможности

- Обработка видео-ссылок через Telegram
- Скачивание видео без использования эмуляторов или логинов (для YouTube и TikTok)
- Скачивание видео из Instagram (требуются учетные данные)
- Отправка обработанных видео пользователю

## Установка

1. Клонируйте репозиторий
2. Создайте виртуальное окружение: `python3 -m venv venv`
3. Активируйте виртуальное окружение: `source venv/bin/activate`
4. Установите зависимости: `pip install -r requirements.txt`
5. Создайте файл `.env` с токеном Telegram бота и учетными данными Instagram:
   ```
   BOT_TOKEN=your_telegram_bot_token
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   DOWNLOAD_PATH=downloads
   TEMP_PATH=temp
   ```

## Запуск

```bash
source venv/bin/activate
python simple_bot.py
```

## Требования

- Python 3.9+
- Библиотеки: telepot, yt-dlp, instaloader, python-dotenv
- Для Instagram: действительные учетные данные

## Использование

1. Найдите бота в Telegram
2. Отправьте команду `/start`
3. Отправьте ссылку на видео из Instagram Reels, TikTok или YouTube Shorts
4. Бот скачает и отправит вам видео 