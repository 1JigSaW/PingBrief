from newspaper import Article
import logging

logger = logging.getLogger(__name__)


class ContentExtractor:
    def __init__(self):
        pass
    
    def extract_content(self, url: str) -> tuple[str | None, str | None]:
        """Extract title and content from web page"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            title = article.title
            content = article.text
            
            if content:
                content = ' '.join(content.split())
            
            return title, content
            
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {e}")
            return None, None 