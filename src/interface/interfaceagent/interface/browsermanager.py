from pydantic import HttpUrl
from uuid import UUID, uuid4
from typing import Dict, Optional, Any, List
from .webbrowser import WebBrowser
from loguru import logger
import asyncio

# Configure loguru
logger.add("api.log", rotation="500 MB", level="INFO")


class WebBrowserManager:
    def __init__(self):
        self.sessions: Dict[UUID, WebBrowser] = {}
        self.lock = asyncio.Lock()

    async def create_session(self, start_url: HttpUrl, headless: bool = True) -> UUID:
        """
        Create a new browser session.

        Args:
            start_url (HttpUrl): The initial URL for the browser session.
            headless (bool): Whether to run the browser in headless mode.

        Returns:
            UUID: The unique identifier for the created session.

        Raises:
            Exception: If there's an error creating the session.
        """
        session_id = uuid4()
        try:
            browser = WebBrowser(str(start_url), headless=headless)
            await browser.initialize()
            async with self.lock:
                self.sessions[session_id] = browser
            logger.info(f"Created new session with ID: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise

    async def get_session(self, session_id: UUID) -> Optional[WebBrowser]:
        """
        Retrieve a browser session by its ID.

        Args:
            session_id (UUID): The unique identifier of the session.

        Returns:
            Optional[WebBrowser]: The WebBrowser instance if found, None otherwise.
        """
        async with self.lock:
            session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
        return session

    async def close_session(self, session_id: UUID) -> None:
        """
        Close a specific browser session.

        Args:
            session_id (UUID): The unique identifier of the session to close.
        """
        async with self.lock:
            if session_id in self.sessions:
                try:
                    await self.sessions[session_id].close()
                    del self.sessions[session_id]
                    logger.info(f"Closed session: {session_id}")
                except Exception as e:
                    logger.error(
                        f"Error closing session {session_id}: {str(e)}")
            else:
                logger.warning(
                    f"Attempted to close non-existent session: {session_id}")

    async def close_all_sessions(self) -> None:
        """Close all active browser sessions."""
        session_ids = list(self.sessions.keys())
        close_tasks = [self.close_session(session_id)
                       for session_id in session_ids]
        await asyncio.gather(*close_tasks)
        logger.info(f"Closed all {len(session_ids)} sessions")

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing session information.
        """
        async with self.lock:
            return [
                {
                    "session_id": str(session_id),
                    "start_url": browser.start_url,
                    "current_url": await self._get_current_url(browser),
                    "headless": browser.headless
                }
                for session_id, browser in self.sessions.items()
            ]

    async def _get_current_url(self, browser: WebBrowser) -> Optional[str]:
        """Helper method to safely get the current URL of a browser session."""
        try:
            return browser.page.url if browser.page else None
        except Exception as e:
            logger.error(f"Error getting current URL: {str(e)}")
            return None

    async def get_session_count(self) -> int:
        """
        Get the number of active sessions.

        Returns:
            int: The number of active sessions.
        """
        async with self.lock:
            return len(self.sessions)

    async def session_exists(self, session_id: UUID) -> bool:
        """
        Check if a session exists.

        Args:
            session_id (UUID): The unique identifier of the session.

        Returns:
            bool: True if the session exists, False otherwise.
        """
        async with self.lock:
            return session_id in self.sessions
