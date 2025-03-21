import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings."""
    def __init__(self):
        # Bot settings
        self.bot_token = os.getenv("BOT_TOKEN", "")
        
        # Download settings
        self.download_path = os.getenv("DOWNLOAD_PATH", "downloads")
        self.temp_path = os.getenv("TEMP_PATH", "temp")
        
        # Max file size in MB that can be sent via Telegram (50MB limit)
        self.max_file_size_mb = 50
        
        # Video sources
        self.supported_sources = [
            "instagram.com",
            "tiktok.com",
            "youtube.com",
            "youtu.be"
        ]

# Create settings instance
settings = Settings()

# Ensure download and temp directories exist
os.makedirs(settings.download_path, exist_ok=True)
os.makedirs(settings.temp_path, exist_ok=True) 