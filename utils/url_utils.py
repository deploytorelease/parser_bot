import re
from typing import Optional, List
from config import settings

def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text message.
    
    Args:
        text: Text message potentially containing URLs
        
    Returns:
        List of extracted URLs
    """
    # URL regex pattern
    url_pattern = re.compile(r'https?://\S+')
    
    # Find all URLs in the text
    return url_pattern.findall(text)

def is_supported_url(url: str) -> bool:
    """
    Check if the URL is from a supported source.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from a supported source, False otherwise
    """
    for source in settings.supported_sources:
        if source in url:
            return True
    return False

def get_clean_url(url: str) -> Optional[str]:
    """
    Clean up URL by removing unnecessary query parameters.
    
    Args:
        url: Original URL
        
    Returns:
        Cleaned URL or None if URL is invalid
    """
    # Basic validation
    if not url.startswith(('http://', 'https://')):
        return None
    
    # Instagram URL cleaning
    if 'instagram.com' in url:
        # Keep only the base URL path removing queries
        match = re.match(r'(https?://(?:www\.)?instagram\.com/(?:reel|p)/[^/?#]+).*', url)
        if match:
            return match.group(1)
    
    # TikTok URL cleaning
    elif 'tiktok.com' in url:
        # TikTok URLs are generally clean already, but remove any tracking parameters
        match = re.match(r'(https?://(?:www\.)?(?:vm\.)?tiktok\.com/[^?#]+).*', url)
        if match:
            return match.group(1)
    
    # YouTube Shorts cleaning
    elif ('youtube.com/shorts' in url) or ('youtu.be' in url):
        # Extract video ID and create clean URL
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
    
    # If no specific cleaning rules matched, return the original URL
    return url 