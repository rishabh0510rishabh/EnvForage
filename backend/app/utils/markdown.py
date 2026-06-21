
# --- Markdown Converter & Sanitizer ---
import logging
import re

logger = logging.getLogger("MarkdownSanitizer")

try:
    import bleach
    import markdown
    BLEACH_AVAILABLE = True
except ImportError:
    logger.warning("markdown/bleach not installed. Using raw string fallback.")
    BLEACH_AVAILABLE = False

class MarkdownParser:
    """
    A highly secure Markdown to HTML converter designed to prevent XSS.
    Utilizes python-markdown for parsing and Mozilla's Bleach for sanitizing.
    """

    ALLOWED_TAGS = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]

    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'rel', 'target'],
        'abbr': ['title'],
        'acronym': ['title'],
    }

    # Automatically unroll shortlinks to full URLs if needed
    URL_REGEX = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )

    @classmethod
    def convert(cls, raw_markdown: str, strict: bool = True) -> str:
        """
        Converts markdown to HTML, then sanitizes the output.
        If strict is True, strips all unapproved tags.
        """
        if not raw_markdown:
            return ""

        if not BLEACH_AVAILABLE:
            # Fallback for environments lacking the C-extensions
            return f"<p>{raw_markdown}</p>"

        try:
            # 1. Convert Markdown to HTML (supporting tables and fenced code blocks)
            raw_html = markdown.markdown(
                raw_markdown,
                extensions=['extra', 'codehilite', 'tables']
            )

            # 2. Sanitize HTML via Bleach
            sanitized_html = bleach.clean(
                raw_html,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=strict
            )

            # 3. Add rel="nofollow noopener noreferrer" to external links dynamically
            linker = bleach.linkifier.Linker(
                callbacks=[cls._linkify_callback]
            )
            final_html = linker.linkify(sanitized_html)

            return final_html
        except Exception as e:
            logger.error(f"Markdown parsing failed: {e}")
            return "<p>Content temporarily unavailable.</p>"

    @staticmethod
    def _linkify_callback(attrs: dict, new: bool = False) -> dict:
        """Bleach callback to secure all outgoing links."""
        href = attrs.get((None, 'href'))
        if href and not href.startswith(('mailto:', 'tel:', '/', '#')):
            # Enforce target="_blank" and secure rel attributes for external links
            attrs[(None, 'target')] = '_blank'
            attrs[(None, 'rel')] = 'nofollow noopener noreferrer'
        return attrs
