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
import ssl
import platform
import subprocess
import tempfile
import requests
import json
import logging
from urllib.parse import urlparse, parse_qs
import urllib3

# Глобальное отключение проверки SSL для Python
ssl._create_default_https_context = ssl._create_unverified_context

# Отключаем предупреждения о небезопасных запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
TEMP_PATH = os.getenv('TEMP_PATH', 'temp')
MAX_FILE_SIZE_MB = float(os.getenv('MAX_FILE_SIZE_MB', 50))

# Создаем временную директорию, если она не существует
os.makedirs(TEMP_PATH, exist_ok=True)

# Функция для извлечения URL из текста
def extract_urls(text):
    """Извлечение URL из текста"""
    # Регулярное выражение для поиска URL
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
    return re.findall(url_pattern, text)

# Функция для проверки поддерживаемых URL
def is_supported_url(url):
    """Проверка, поддерживается ли URL"""
    supported_domains = [
        'youtube.com', 'youtu.be',  # YouTube и YouTube Shorts
        'instagram.com',            # Instagram
        'tiktok.com'                # TikTok
    ]
    
    domain = urlparse(url).netloc
    return any(d in domain for d in supported_domains)

# Функция для очистки URL
def clean_url(url):
    """Очистка URL от трекеров и параметров"""
    if not url:
        return url
        
    # Очистка URL YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        # Извлекаем ID видео для YouTube
        if 'youtube.com/shorts/' in url:
            video_id_match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]+)', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return f"https://www.youtube.com/shorts/{video_id}"
        elif 'youtu.be' in url:
            video_id_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                return f"https://youtu.be/{video_id}"
    
    return url

# Функция для скачивания видео
def download_video(url, source_type=None):
    """Скачивание видео по URL"""
    try:
        # Принудительно отключаем проверку SSL сертификатов
        old_https_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        logger.info(f"Определяем тип источника для URL: {url}")
        
        # Если источник не указан, определяем его
        if not source_type:
            source_type = determine_source_type(url)
        
        logger.info(f"Тип источника: {source_type}")
        
        # Приводим к нижнему регистру для унификации
        source_type = source_type.lower()
        
        # Создаем уникальный ID для скачивания
        download_id = str(uuid.uuid4())
        output_file = os.path.join(TEMP_PATH, f"{download_id}.mp4")
        
        # Если это YouTube Shorts, используем специальный метод для загрузки
        if source_type == "youtube" and "shorts" in url:
            try:
                logger.info(f"Загрузка YouTube Shorts с помощью специального метода: {url}")
                result = download_youtube_shorts(url)
                if result:
                    return {
                        "file": result,
                        "download_id": download_id,
                        "success": True,
                        "method": "custom_shorts_downloader"
                    }
            except Exception as e:
                logger.error(f"Ошибка при скачивании YouTube Shorts: {str(e)}")
        
        # Для YouTube используем pytube
        if source_type == "youtube":
            try:
                logger.info(f"Загрузка YouTube видео через pytube: {url}")
                from pytube import YouTube
                
                # Отключаем проверку SSL в requests
                import requests
                requests.packages.urllib3.disable_warnings()
                session = requests.Session()
                session.verify = False
                
                # Пробуем скачать видео через pytube
                yt = YouTube(url)
                # Получаем самое высокое разрешение
                stream = yt.streams.get_highest_resolution()
                
                if stream:
                    # Скачиваем видео
                    stream.download(output_path=TEMP_PATH, filename=f"{download_id}.mp4")
                    
                    # Проверяем результат
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 10000:
                        return {
                            "file": output_file,
                            "download_id": download_id,
                            "success": True,
                            "method": "pytube"
                        }
            except Exception as e:
                logger.error(f"Ошибка при скачивании с pytube: {str(e)}")
        
        # Если pytube не сработал или это не YouTube, используем yt-dlp через subprocess
        try:
            logger.info(f"Попытка скачивания через командную строку для {url}")
            # Формируем команду для yt-dlp с отключением проверки сертификатов
            cmd = [
                'yt-dlp',
                '--no-check-certificate',  # Отключаем проверку сертификатов
                '--force-ipv4',            # Принудительно используем IPv4
                '--geo-bypass',            # Обходим гео-ограничения
                '--prefer-insecure',       # Предпочитаем небезопасные соединения
                '--ignore-errors',         # Игнорируем некритические ошибки
                '--force-generic-extractor', # Используем обобщенный экстрактор при необходимости
                '-f', 'best[ext=mp4]/best',  # Выбираем лучший формат MP4
                '-o', output_file,      # Указываем путь для сохранения
                url                          # URL для скачивания
            ]
            
            # Выполняем команду
            try:
                process = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Проверяем результат
                if process.returncode == 0 and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file) / (1024 * 1024)  # в МБ
                    logger.info(f"yt-dlp успешно скачал видео, размер: {file_size:.2f} МБ")
                    
                    if file_size < 0.1:  # Если файл слишком маленький, это может быть ошибка
                        logger.warning(f"Скачанный файл слишком маленький ({file_size:.2f} МБ), возможно это превью")
                        return None
                    
                    return {
                        "file": output_file,
                        "download_id": download_id,
                        "success": True,
                        "source_type": source_type
                    }
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка при использовании командной строки yt-dlp: {str(e)}")
                
                # В случае ошибки пробуем последнюю попытку с другими параметрами
                try:
                    # Пробуем версию с меньшим количеством опций
                    alternative_cmd = [
                        'yt-dlp', 
                        '--no-check-certificate',
                        '--ignore-errors',
                        '--no-warnings',
                        '-f', 'best',
                        '-o', output_file,
                        url
                    ]
                    
                    process = subprocess.run(alternative_cmd, capture_output=True, text=True, check=True)
                    
                    if process.returncode == 0 and os.path.exists(output_file):
                        file_size = os.path.getsize(output_file) / (1024 * 1024)  # в МБ
                        logger.info(f"yt-dlp (простая версия) успешно скачал видео, размер: {file_size:.2f} МБ")
                        
                        if file_size < 0.1:
                            logger.warning(f"Скачанный файл слишком маленький ({file_size:.2f} МБ)")
                            return None
                        
                        return {
                            "file": output_file,
                            "download_id": download_id,
                            "success": True,
                            "source_type": source_type
                        }
                except Exception as e:
                    logger.error(f"Ошибка при финальной попытке: {str(e)}")
        
        except Exception as e:
            logger.error(f"Ошибка при использовании командной строки: {str(e)}")
        
        # Восстанавливаем контекст SSL
        ssl._create_default_https_context = old_https_context
        
        # Если все методы не сработали, возвращаем None
        logger.error(f"Не удалось скачать видео: {url}")
        return None
    
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при скачивании видео: {str(e)}")
        return None

# Функция для скачивания YouTube Shorts
def download_youtube_shorts(url):
    """Загрузка YouTube видео с помощью последней версии yt-dlp"""
    logger.info(f"Скачиваем YouTube видео: {url}")
    
    # Создаем уникальное имя файла
    file_name = f"{TEMP_PATH}/{uuid.uuid4()}.mp4"
    
    try:
        # Используем упрощенную конфигурацию yt-dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Лучшее качество mp4
            'outtmpl': file_name,            # Имя выходного файла
            'nocheckcertificate': True,      # Отключаем проверку сертификатов
            'no_warnings': True,
            'ignoreerrors': False,
            'verbose': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Начинаем загрузку с yt-dlp...")
            info = ydl.extract_info(url, download=True)
            
            # Проверяем размер файла
            if os.path.exists(file_name):
                file_size = os.path.getsize(file_name) / (1024 * 1024)
                logger.info(f"Видео скачано: {info.get('title', 'Unknown')}, размер: {file_size:.2f} МБ")
                
                if file_size < 0.1:  # Проверка на минимальный размер файла
                    logger.warning(f"Файл слишком маленький ({file_size:.2f} МБ)")
                    return None
                    
                return file_name
    except Exception as e:
        logger.error(f"Ошибка при скачивании видео: {e}")
        return None

# Функция определения типа источника
def determine_source_type(url):
    """Определяет тип источника видео по URL"""
    if re.search(r'(youtube\.com|youtu\.be)', url):
        return "YouTube"
    elif re.search(r'instagram\.com', url):
        return "Instagram"
    elif re.search(r'tiktok\.com', url):
        return "TikTok"
    else:
        return "Unknown"

# Очистка файла
def cleanup_file(file_path):
    """Удаление временного файла"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Ошибка при очистке файла {file_path}: {str(e)}")
    return False

# Обработчики команд
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

def handle_message(msg):
    """Обработка входящих сообщений с URL"""
    content_type, chat_type, chat_id = telepot.glance(msg)
    
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
            # Скачиваем видео с использованием улучшенной функции
            source_type = determine_source_type(clean_url_result)
            video_data = download_video(clean_url_result, source_type)
            
            if not video_data or not os.path.exists(video_data.get("file")):
                bot.editMessageText((chat_id, status_msg_id), 
                    "❌ Не удалось загрузить видео. Возможно, оно недоступно или приватное."
                )
                return
                
            # Проверяем размер файла
            file_size_bytes = os.path.getsize(video_data.get("file"))
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                bot.editMessageText((chat_id, status_msg_id), 
                    f"❌ Видео слишком большое ({file_size_mb:.1f} MB). "
                    f"Максимальный размер: {MAX_FILE_SIZE_MB} MB."
                )
                # Удаляем скачанный файл
                cleanup_file(video_data.get("file"))
                return
            
            # Обновляем статус
            bot.editMessageText((chat_id, status_msg_id), "📤 Загружаю видео в Telegram...")
            
            # Отправляем видео
            with open(video_data.get("file"), 'rb') as video_file:
                bot.sendVideo(
                    chat_id,
                    video_file,
                    caption=f"📹 Видео из {source_type}",
                    supports_streaming=True
                )
            
            # Обновляем сообщение о статусе
            bot.editMessageText((chat_id, status_msg_id), "✅ Видео успешно загружено!")
            
            # Удаляем скачанный файл
            cleanup_file(video_data.get("file"))
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

# Запускаем основную функцию
if __name__ == "__main__":
    logger.info("Бот запущен...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.") 