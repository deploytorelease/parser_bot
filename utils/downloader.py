import os
import uuid
import yt_dlp
from typing import Optional, Dict, Any
from loguru import logger
from config import settings

class VideoDownloader:
    """Class to handle downloading videos from various platforms."""
    
    def __init__(self):
        # Base YT-DLP options
        self.base_options = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(settings.temp_path, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
        }
    
    def _get_source_type(self, url: str) -> Optional[str]:
        """Determine the source type based on URL."""
        if "instagram.com" in url:
            return "instagram"
        elif "tiktok.com" in url:
            return "tiktok"
        elif "youtube.com" in url or "youtu.be" in url:
            if "/shorts/" in url:
                return "youtube_shorts"
            return "youtube"
        return None
    
    def download(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Download video from URL.
        
        Args:
            url: URL of the video to download
            
        Returns:
            Dictionary with video information including path to downloaded file
        """
        source_type = self._get_source_type(url)
        if not source_type:
            logger.error(f"Unsupported URL: {url}")
            return None
        
        # Generate a unique ID for this download
        download_id = str(uuid.uuid4())
        
        # Create options for this specific download
        options = self.base_options.copy()
        
        # Adjust options based on source type
        if source_type == "instagram":
            # Instagram-specific options
            options.update({
                'cookiesfrombrowser': None,  # No cookies needed
                'extractor_args': {'instagram': {'skip_download': False}},
            })
        elif source_type == "tiktok":
            # TikTok-specific options
            options.update({
                'cookiesfrombrowser': None,  # No cookies needed
                'extractor_args': {'tiktok': {'skip_download': False}},
            })
        
        # Set a specific output template for this download
        options['outtmpl'] = os.path.join(settings.temp_path, f"{download_id}.%(ext)s")
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    logger.error(f"Failed to extract info from URL: {url}")
                    return None
                
                # Find the downloaded file
                if 'entries' in info:
                    # Playlist/multiple entries, we take the first
                    info = info['entries'][0]
                
                # Determine the file path
                downloaded_file = os.path.join(settings.temp_path, f"{download_id}.{info.get('ext', 'mp4')}")
                
                # If file doesn't exist, try to find it with various extensions
                if not os.path.exists(downloaded_file):
                    for ext in ['mp4', 'webm', 'mkv']:
                        potential_file = os.path.join(settings.temp_path, f"{download_id}.{ext}")
                        if os.path.exists(potential_file):
                            downloaded_file = potential_file
                            break
                
                # Return video info
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
            logger.error(f"Error downloading {source_type} video: {str(e)}")
            return None
    
    def cleanup(self, file_path: str) -> bool:
        """Remove a downloaded file to clean up space."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {str(e)}")
        return False 