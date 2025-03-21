import os
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from utils import VideoDownloader, extract_urls, is_supported_url, get_clean_url
from config import settings

# Initialize video downloader
downloader = VideoDownloader()

def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Отправь мне ссылку на видео из Instagram Reels, TikTok или YouTube Shorts, "
        "и я скачаю его для тебя.\n\n"
        "Просто вставь ссылку в сообщение, и я сразу начну работу!"
    )

def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    update.message.reply_text(
        "🔍 Как пользоваться ботом:\n\n"
        "1. Найди видео в Instagram Reels, TikTok или YouTube Shorts\n"
        "2. Скопируй ссылку на видео\n"
        "3. Отправь эту ссылку мне в сообщении\n"
        "4. Дождись, пока я скачаю и отправлю тебе видео\n\n"
        "⚠️ Обрати внимание: я могу скачивать только публичные видео."
    )

def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process messages containing URLs."""
    # Extract URLs from the message
    message_text = update.message.text
    urls = extract_urls(message_text)
    
    if not urls:
        update.message.reply_text(
            "Я не нашел ссылок в твоем сообщении. Пожалуйста, отправь мне ссылку на "
            "видео из Instagram Reels, TikTok или YouTube Shorts."
        )
        return
    
    # Process the first valid URL
    for url in urls:
        # Check if URL is from a supported source
        if not is_supported_url(url):
            continue
        
        # Clean the URL
        clean_url = get_clean_url(url)
        if not clean_url:
            continue
        
        # Notify user that download is starting
        status_message = update.message.reply_text(
            "⏳ Начинаю загрузку видео... Это может занять некоторое время."
        )
        
        try:
            # Download the video
            video_info = downloader.download(clean_url)
            
            if not video_info or not os.path.exists(video_info['file_path']):
                status_message.edit_text(
                    "❌ Не удалось загрузить видео. Возможно, оно недоступно или приватное."
                )
                return
            
            # Check file size
            file_size_bytes = os.path.getsize(video_info['file_path'])
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_mb > settings.max_file_size_mb:
                status_message.edit_text(
                    f"❌ Видео слишком большое ({file_size_mb:.1f} MB). "
                    f"Максимальный размер: {settings.max_file_size_mb} MB."
                )
                # Clean up the downloaded file
                downloader.cleanup(video_info['file_path'])
                return
            
            # Update status
            status_message.edit_text("📤 Загружаю видео в Telegram...")
            
            # Send the video
            with open(video_info['file_path'], 'rb') as video_file:
                update.message.reply_video(
                    video=video_file,
                    caption=f"📹 {video_info['title']}",
                    supports_streaming=True,
                )
            
            # Update status message
            status_message.edit_text("✅ Видео успешно загружено!")
            
            # Clean up the downloaded file
            downloader.cleanup(video_info['file_path'])
            return
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            status_message.edit_text(
                "❌ Произошла ошибка при обработке видео. Пожалуйста, попробуйте другую ссылку."
            )
            return
    
    # If no valid URLs were found
    update.message.reply_text(
        "❌ Я не смог распознать ссылку на поддерживаемое видео. "
        "Пожалуйста, убедитесь, что вы отправляете ссылку на Instagram Reels, TikTok или YouTube Shorts."
    )

def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send message to the user
    if update and update.effective_message:
        update.effective_message.reply_text(
            "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
        ) 