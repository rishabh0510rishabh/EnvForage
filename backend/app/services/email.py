
# --- Abstract Email Dispatcher ---
import asyncio
import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger("EmailDispatcher")

class EmailProvider(ABC):
    @abstractmethod
    async def send(self, to: list[str], subject: str, html_body: str) -> bool:
        pass

class SMTPEmailProvider(EmailProvider):
    """Fallback standard SMTP provider."""
    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    async def send(self, to: list[str], subject: str, html_body: str) -> bool:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.user
        msg['To'] = ", ".join(to)
        msg.set_content("Please enable HTML to view this message.")
        msg.add_alternative(html_body, subtype='html')

        try:
            # We run SMTP in a threadpool to avoid blocking the async event loop
            await asyncio.to_thread(self._send_sync, msg)
            return True
        except Exception as e:
            logger.error(f"SMTP failed to send email to {to}: {e}")
            return False

    def _send_sync(self, msg: EmailMessage):
        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)

class MockSendGridProvider(EmailProvider):
    """Example integration with a 3rd party REST API."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def send(self, to: list[str], subject: str, html_body: str) -> bool:
        logger.info(f"Simulating SendGrid dispatch to {to}")
        await asyncio.sleep(0.5) # Simulate network latency
        return True

class EmailDispatcher:
    """
    A robust orchestrator managing multiple email providers.
    Implements automatic failover (e.g., tries SendGrid, falls back to SMTP)
    and asynchronous retry logic with exponential backoff.
    """
    def __init__(self, primary: EmailProvider, fallback: EmailProvider | None = None):
        self.primary = primary
        self.fallback = fallback

    async def dispatch(self, to: list[str], subject: str, context: dict[str, Any], template_name: str) -> bool:
        html_body = self._render_template(template_name, context)

        success = await self._attempt_send(self.primary, to, subject, html_body)

        if not success and self.fallback:
            logger.warning(f"Primary provider failed. Attempting fallback for {to}")
            success = await self._attempt_send(self.fallback, to, subject, html_body)

        if not success:
            logger.critical(f"All email providers failed to dispatch to {to}")

        return success

    async def _attempt_send(self, provider: EmailProvider, to: list[str], subject: str, body: str, retries=2) -> bool:
        for attempt in range(retries):
            if await provider.send(to, subject, body):
                return True
            logger.warning(f"Provider {provider.__class__.__name__} attempt {attempt+1} failed.")
            await asyncio.sleep(2 ** attempt)
        return False

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        from jinja2 import Environment, select_autoescape

        # Use Jinja2 with autoescape to prevent HTML/XSS injection
        # from user-controlled context values.
        env = Environment(autoescape=select_autoescape(["html"]))
        template = env.from_string(
            "<h1>{{ template_name }}</h1>"
            "{% for key, val in data.items() %}"
            "<p><strong>{{ key }}:</strong> {{ val }}</p>"
            "{% endfor %}"
        )
        return template.render(template_name=template_name, data=context)
