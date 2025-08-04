import logging
import requests
from typing import List, Tuple
from urllib.parse import urlparse
from config import (
    IMAGE_HEAD_TIMEOUT, IMAGE_GET_TIMEOUT, 
    IMAGE_GET_MAX_SIZE, MAX_IMAGE_SIZE
)

logger = logging.getLogger(__name__)

class ImageValidator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Generation-Service/1.0.0'
        })
    
    def validate_url_format(self, url: str) -> bool:
        """
        Basic URL format validation
        """
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ['http', 'https'], parsed.netloc])
        except Exception:
            return False
    
    def check_image_accessibility(self, url: str) -> Tuple[bool, str]:
        """
        Check if image URL is accessible and valid
        Returns (is_valid, error_message)
        """
        if not self.validate_url_format(url):
            return False, "Invalid URL format"
        
        try:
            # Try HEAD request first
            response = self.session.head(url, timeout=IMAGE_HEAD_TIMEOUT, allow_redirects=True)
            
            if response.status_code >= 200 and response.status_code < 300:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if not content_type.startswith('image/'):
                    return False, f"Invalid content type: {content_type}"
                
                # Check content length
                content_length = response.headers.get('Content-Length')
                if content_length:
                    try:
                        size = int(content_length)
                        if size > MAX_IMAGE_SIZE:
                            return False, f"Image too large: {size} bytes > {MAX_IMAGE_SIZE}"
                    except ValueError:
                        pass
                
                return True, ""
            
            # If HEAD fails, try GET with limited size
            response = self.session.get(
                url, 
                timeout=IMAGE_GET_TIMEOUT, 
                stream=True,
                headers={'Range': f'bytes=0-{IMAGE_GET_MAX_SIZE}'}
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                content_type = response.headers.get('Content-Type', '').lower()
                if not content_type.startswith('image/'):
                    return False, f"Invalid content type: {content_type}"
                return True, ""
            
            return False, f"HTTP {response.status_code}"
            
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def validate_images(self, image_urls: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate list of image URLs
        Returns (valid_urls, unreachable_urls)
        """
        valid_urls = []
        unreachable_urls = []
        consecutive_failures = 0
        
        for url in image_urls:
            is_valid, error_msg = self.check_image_accessibility(url)
            
            if is_valid:
                valid_urls.append(url)
                consecutive_failures = 0
            else:
                unreachable_urls.append(url)
                consecutive_failures += 1
                logger.warning(f"Image validation failed for {url}: {error_msg}")
                
                # Stop validation if too many consecutive failures
                if consecutive_failures >= 2:
                    logger.warning("Too many consecutive image validation failures, marking remaining as unreachable")
                    unreachable_urls.extend(image_urls[len(valid_urls) + len(unreachable_urls):])
                    break
        
        return valid_urls, unreachable_urls
    
    def check_image_threshold(self, total_images: int, valid_images: int) -> bool:
        """
        Check if we have enough valid images (> 30% threshold)
        """
        if total_images == 0:
            return False
        
        if valid_images == 0:
            return False
        
        threshold = 0.3
        ratio = valid_images / total_images
        return ratio > threshold
