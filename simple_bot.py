#!/usr/bin/env python3
import os
import sys
import time
import re
import uuid
import telepot
from telepot.loop import MessageLoop
from dotenv import load_dotenv
import yt_dlp
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("bot.log", rotation="10 MB", level="INFO")

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в .env файле")
    sys.exit(1)

# Instagram credentials
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# Пути для скачивания
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "downloads")
TEMP_PATH = os.getenv("TEMP_PATH", "temp")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(TEMP_PATH, exist_ok=True)

# Поддерживаемые источники
SUPPORTED_SOURCES = ["instagram.com", "tiktok.com", "youtube.com", "youtu.be"]

# Максимальный размер файла в МБ
MAX_FILE_SIZE_MB = 50

def extract_urls(text):
    """Извлечение URL из текста"""
    url_pattern = re.compile(r'https?://\S+')
    return url_pattern.findall(text)

def is_supported_url(url):
    """Проверка, поддерживается ли URL"""
    for source in SUPPORTED_SOURCES:
        if source in url:
            return True
    return False

def clean_url(url):
    """Очистка URL от лишних параметров"""
    if not url.startswith(('http://', 'https://')):
        return None
    
    # Instagram URL cleaning
    if 'instagram.com' in url:
        match = re.match(r'(https?://(?:www\.)?instagram\.com/(?:reel|p)/[^/?#]+).*', url)
        if match:
            return match.group(1)
    
    # TikTok URL cleaning
    elif 'tiktok.com' in url:
        match = re.match(r'(https?://(?:www\.)?(?:vm\.)?tiktok\.com/[^?#]+).*', url)
        if match:
            return match.group(1)
    
    # YouTube Shorts cleaning
    elif ('youtube.com/shorts' in url) or ('youtu.be' in url):
        if '/shorts/' in url:
            video_id_match = re.search(r'/shorts/([a-zA-Z0-9_-]+)', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return f"https://www.youtube.com/shorts/{video_id}"
        elif 'youtu.be' in url:
            video_id_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return f"https://youtu.be/{video_id}"
    
    return url

def download_video(url):
    """Скачивание видео по URL"""
    # Определяем тип источника
    source_type = None
    if "instagram.com" in url:
        source_type = "instagram"
    elif "tiktok.com" in url:
        source_type = "tiktok"
    elif "youtube.com" in url or "youtu.be" in url:
        if "/shorts/" in url:
            source_type = "youtube_shorts"
        else:
            source_type = "youtube"
    
    if not source_type:
        logger.error(f"Неподдерживаемый URL: {url}")
        return None
    
    # Генерируем уникальный ID для загрузки
    download_id = str(uuid.uuid4())
    
    # Базовые опции для yt-dlp
    options = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(TEMP_PATH, f"{download_id}.%(ext)s"),
        'quiet': False,  # Показывать вывод для отладки
        'no_warnings': False,  # Показывать предупреждения для отладки
        'ignoreerrors': False,
    }
    
    # Настраиваем опции в зависимости от источника
    if source_type == "instagram":
        # Для Instagram нужно использовать более продвинутые методы
        try:
            # Пытаемся загрузить через instaloader (если установлен)
            import importlib.util
            if importlib.util.find_spec("instaloader"):
                return download_with_instaloader(url, download_id)
            else:
                # Альтернативный подход с yt-dlp
                options.update({
                    'cookiesfrombrowser': ('chrome', ),  # Берем cookies из Chrome
                    'extractor_args': {'instagram': {'skip_download': False}},
                })
        except ImportError:
            logger.info("instaloader не установлен, используем резервный метод")
            # Продолжаем с yt-dlp
    elif source_type == "tiktok":
        # TikTok-специфичные опции
        options.update({
            'cookiesfrombrowser': None,  # Cookies не нужны
            'extractor_args': {'tiktok': {'skip_download': False}},
        })
    
    # Set a specific output template for this download
    options['outtmpl'] = os.path.join(TEMP_PATH, f"{download_id}.%(ext)s")
    
    try:
        logger.info(f"Начинаю загрузку {source_type} видео: {url}")
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                logger.error(f"Не удалось получить информацию из URL: {url}")
                return None
            
            # Находим скачанный файл
            if 'entries' in info:
                # Плейлист/несколько записей, берем первую
                info = info['entries'][0]
            
            # Определяем путь к файлу
            downloaded_file = os.path.join(TEMP_PATH, f"{download_id}.{info.get('ext', 'mp4')}")
            
            # Если файл не существует, пробуем найти его с разными расширениями
            if not os.path.exists(downloaded_file):
                for ext in ['mp4', 'webm', 'mkv']:
                    potential_file = os.path.join(TEMP_PATH, f"{download_id}.{ext}")
                    if os.path.exists(potential_file):
                        downloaded_file = potential_file
                        break
            
            # Возвращаем информацию о видео
            return {
                'id': download_id,
                'title': info.get('title', 'Unknown'),
                'source': source_type,
                'file_path': downloaded_file,
                'duration': info.get('duration'),
                'width': info.get('width'),
                'height': info.get('height'),
            }
    except Exception as e:
        logger.error(f"Ошибка при скачивании {source_type} видео: {str(e)}")
        return None

def download_with_instaloader(url, download_id):
    """Скачивание видео из Instagram с помощью instaloader"""
    try:
        # Импортируем библиотеку
        import instaloader
        import re
        
        # Создаем экземпляр загрузчика
        L = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            dirname_pattern=TEMP_PATH
        )
        
        # Авторизуемся если есть учетные данные
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            logger.info(f"Авторизация в Instagram с пользователем {INSTAGRAM_USERNAME}")
            try:
                L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                logger.info("Авторизация в Instagram успешна")
            except Exception as e:
                logger.error(f"Ошибка авторизации в Instagram: {str(e)}")
                # Продолжаем без авторизации
        
        # Пытаемся извлечь shortcode из URL
        match = re.search(r"instagram\.com/(?:p|reel)/([^/?]+)", url)
        if not match:
            logger.error(f"Не удалось извлечь shortcode из URL: {url}")
            return None
        
        shortcode = match.group(1)
        logger.info(f"Извлечен shortcode: {shortcode}")
        
        # Скачиваем пост
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Создаем временную директорию для скачивания
        temp_dir = os.path.join(TEMP_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Сохраняем текущую директорию и меняем на временную
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        # Скачиваем видео
        logger.info(f"Скачивание поста {shortcode} в {temp_dir}")
        L.download_post(post, target=download_id)
        
        # Возвращаемся в исходную директорию
        os.chdir(old_cwd)
        
        # Ищем видео файл
        video_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.mp4'):
                    video_files.append(os.path.join(root, file))
        
        if not video_files:
            logger.error(f"Видео не найдено в {temp_dir}")
            return None
        
        # Используем первый найденный видео файл
        video_file = video_files[0]
        logger.info(f"Найден видео файл: {video_file}")
        
        # Копируем в основную директорию
        target_file = os.path.join(TEMP_PATH, f"{download_id}.mp4")
        import shutil
        shutil.copy(video_file, target_file)
        
        # Удаляем временную директорию
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return {
            'id': download_id,
            'title': getattr(post, 'caption', 'Instagram Video') or 'Instagram Video',
            'source': 'instagram',
            'file_path': target_file,
            'duration': None,
            'width': None,
            'height': None,
        }
    except Exception as e:
        logger.error(f"Ошибка при использовании instaloader: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def cleanup_file(file_path):
    """Удаление файла"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Ошибка при очистке файла {file_path}: {str(e)}")
    return False

def handle_message(msg):
    """Обработка входящих сообщений"""
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    if content_type != 'text':
        bot.sendMessage(chat_id, "Пожалуйста, отправьте мне ссылку на видео.")
        return
    
    # Извлекаем URL из сообщения
    urls = extract_urls(msg['text'])
    
    if not urls:
        bot.sendMessage(chat_id, 
            "Я не нашел ссылок в вашем сообщении. Пожалуйста, отправьте мне ссылку на "
            "видео из Instagram Reels, TikTok или YouTube Shorts."
        )
        return
    
    # Обрабатываем первый валидный URL
    for url in urls:
        # Проверяем, поддерживается ли URL
        if not is_supported_url(url):
            continue
        
        # Очищаем URL
        clean_url_result = clean_url(url)
        if not clean_url_result:
            continue
        
        # Уведомляем пользователя о начале загрузки
        status_msg_id = bot.sendMessage(chat_id, 
            "⏳ Начинаю загрузку видео... Это может занять некоторое время."
        )['message_id']
        
        try:
            # Скачиваем видео
            video_info = download_video(clean_url_result)
            
            if not video_info or not os.path.exists(video_info['file_path']):
                bot.editMessageText((chat_id, status_msg_id), 
                    "❌ Не удалось загрузить видео. Возможно, оно недоступно или приватное."
                )
                return
            
            # Проверяем размер файла
            file_size_bytes = os.path.getsize(video_info['file_path'])
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                bot.editMessageText((chat_id, status_msg_id), 
                    f"❌ Видео слишком большое ({file_size_mb:.1f} MB). "
                    f"Максимальный размер: {MAX_FILE_SIZE_MB} MB."
                )
                # Удаляем скачанный файл
                cleanup_file(video_info['file_path'])
                return
            
            # Обновляем статус
            bot.editMessageText((chat_id, status_msg_id), "📤 Загружаю видео в Telegram...")
            
            # Отправляем видео
            with open(video_info['file_path'], 'rb') as video_file:
                bot.sendVideo(
                    chat_id,
                    video_file,
                    caption=f"📹 {video_info['title']}",
                    supports_streaming=True
                )
            
            # Обновляем сообщение о статусе
            bot.editMessageText((chat_id, status_msg_id), "✅ Видео успешно загружено!")
            
            # Удаляем скачанный файл
            cleanup_file(video_info['file_path'])
            return
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {str(e)}")
            bot.editMessageText((chat_id, status_msg_id), 
                "❌ Произошла ошибка при обработке видео. Пожалуйста, попробуйте другую ссылку."
            )
            return
    
    # Если не найдено валидных URL
    bot.sendMessage(chat_id,
        "❌ Я не смог распознать ссылку на поддерживаемое видео. "
        "Пожалуйста, убедитесь, что вы отправляете ссылку на Instagram Reels, TikTok или YouTube Shorts."
    )

def handle_start(chat_id, user_first_name):
    """Отправка приветственного сообщения"""
    bot.sendMessage(chat_id,
        f"Привет, {user_first_name}! 👋\n\n"
        "Отправь мне ссылку на видео из Instagram Reels, TikTok или YouTube Shorts, "
        "и я скачаю его для тебя.\n\n"
        "Просто вставь ссылку в сообщение, и я сразу начну работу!"
    )

def handle_help(chat_id):
    """Отправка справочного сообщения"""
    bot.sendMessage(chat_id,
        "🔍 Как пользоваться ботом:\n\n"
        "1. Найди видео в Instagram Reels, TikTok или YouTube Shorts\n"
        "2. Скопируй ссылку на видео\n"
        "3. Отправь эту ссылку мне в сообщении\n"
        "4. Дождись, пока я скачаю и отправлю тебе видео\n\n"
        "⚠️ Обрати внимание: я могу скачивать только публичные видео."
    )

def on_chat_message(msg):
    """Обработка сообщений пользователя"""
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    if content_type != 'text':
        bot.sendMessage(chat_id, "Пожалуйста, отправьте мне ссылку на видео.")
        return
    
    text = msg['text']
    
    # Обработка команд
    if text.startswith('/start'):
        user_first_name = msg.get('from', {}).get('first_name', 'пользователь')
        handle_start(chat_id, user_first_name)
    elif text.startswith('/help'):
        handle_help(chat_id)
    else:
        # Обработка сообщений с URL
        handle_message(msg)

# Инициализация бота
bot = telepot.Bot(BOT_TOKEN)
MessageLoop(bot, on_chat_message).run_as_thread()

logger.info("Бот запущен...")

# Держим программу запущенной
try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    logger.info("Бот остановлен пользователем.")
except Exception as e:
    logger.error(f"Бот остановлен из-за ошибки: {str(e)}")
    sys.exit(1) 