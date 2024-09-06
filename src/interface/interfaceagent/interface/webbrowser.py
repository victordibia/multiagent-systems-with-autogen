import asyncio
from playwright.async_api import async_playwright, Page, ElementHandle, Locator, TimeoutError as PlaywrightTimeoutError
from typing import Optional, Dict, Any, List, Union, Tuple
from loguru import logger
from interfaceagent.datamodel import BrowserAction


class WebBrowser:
    def __init__(self, start_url: str, headless: bool = True):
        """
        Initialize the WebBrowser.

        Args:
            start_url (str): The initial URL to navigate to.
            headless (bool): Whether to run the browser in headless mode.
        """
        self.start_url: str = start_url
        self.headless: bool = headless
        self.action_history: List[tuple] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_initialized: bool = False

    async def initialize(self) -> None:
        """Initialize the browser and navigate to the start URL."""
        if self.is_initialized:
            logger.warning("WebBrowser is already initialized.")
            return

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            await self.page.goto(self.start_url)
            self.is_initialized = True
            logger.info("WebBrowser successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            await self.close()  # Ensure resources are cleaned up if initialization fails
            raise

    async def action(self, action: BrowserAction) -> None:
        """
        Perform a browser action.

        Args:
            action (BrowserAction): The action to perform.

        Raises:
            ValueError: If the action is unsupported.
            TimeoutError: If the element is not found within the timeout.
        """

        if not self.is_initialized:
            raise RuntimeError(
                "WebBrowser is not initialized. Call initialize() first.")

        try:
            if action.action == "navigate":
                await self.page.goto(action.value)
            else:
                element = self.page.locator(action.selector).first
                await self._handle_element_action(element, action)

            self.action_history.append(
                (action.action, action.selector, action.value))
        except TimeoutError:
            logger.error(
                f"Timeout error: The element with selector '{action.selector}' was not found.")
            raise
        except Exception as e:
            logger.error(
                f"An error occurred while performing the action: {str(e)}")
            raise

    async def _handle_element_action(self, element: Locator, action: BrowserAction) -> None:
        """Handle actions on a specific element with improved waiting and scrolling."""
        try:

            # Try to scroll to the element
            # await self._scroll_to_element(element)

            # Wait for the element to be visible
            await element.wait_for(state="visible")

            # Perform the action
            if action.action == "click":
                await element.click()
            elif action.action == "type":
                await element.fill(action.value)
            elif action.action == "press":
                await element.press(action.value)
            elif action.action == "select":
                await element.select_option(action.value)
            elif action.action == "submit":
                await self._versatile_submit(element)
            else:
                raise ValueError(f"Unsupported action: {action.action}")

            # Wait for network idle after the action
            await self.page.wait_for_load_state('networkidle')
        except PlaywrightTimeoutError:
            # If timeout occurs, try to get more information about the page state
            logger.error(
                f"Timeout occurred. Current URL: {self.page.url}, action: {action}")
            logger.error(f"Page title: {await self.page.title()}")

    async def _versatile_submit(self, element: Locator) -> None:
        """Attempt to submit a form or click a submit-like element."""
        try:
            # First, check if the element is an input
            is_input = await element.evaluate("el => el.tagName.toLowerCase() === 'input'")
            if is_input:
                # Try pressing Enter on the input
                await element.press('Enter')
                await self.page.wait_for_load_state('networkidle')
                return

            # If not an input or Enter didn't work, proceed with the existing logic
            is_form = await element.evaluate("el => el.tagName.toLowerCase() === 'form'")
            if is_form:
                await element.evaluate("form => form.submit()")
            else:
                form = await element.evaluate("el => el.closest('form') ? true : false")
                if form:
                    await element.evaluate("el => el.closest('form').submit()")
                else:
                    await element.click()

            await self.page.wait_for_load_state('networkidle')
        except Exception as e:
            logger.error(
                f"Submit action failed: {str(e)}. Attempting to click the element.")
            await element.click()
            await self.page.wait_for_load_state('networkidle')

    async def screenshot(self, file_path: str = None) -> None:
        """Take a screenshot of the current page."""
        if not file_path:
            file_path = "screenshot.png"
        await self.page.screenshot(path=file_path)
        return file_path

    async def get_html(self) -> str:
        """Get the HTML content of the current page."""
        return await self.page.content()

    async def get_interactive_elements(self) -> List[Dict[str, str]]:
        """Get information about all interactive elements on the page."""
        interactive_elements = []
        selectors = [
            'a[href]', 'button', 'input', 'select', 'textarea',
            '[role="button"]', '[role="link"]', '[role="checkbox"]',
            '[role="menuitem"]', '[role="option"]', '[contenteditable="true"]'
        ]
        all_selectors = ', '.join(selectors)
        elements = await self.page.query_selector_all(all_selectors)

        for element in elements:
            if await element.is_visible():
                element_info = await self._get_element_info(element)
                interactive_elements.append(element_info)

        logger.info(
            f"Total interactive elements found: {len(interactive_elements)}")
        return interactive_elements

    async def _get_element_info(self, element: ElementHandle) -> Dict[str, str]:
        """Get detailed information about an element, including a CSS selector."""
        tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
        element_info = {
            'tag': tag_name,
            'type': await element.get_attribute('type'),
            'role': await element.get_attribute('role'),
            'text': (await element.inner_text()).strip(),
            'id': await element.get_attribute('id'),
            'name': await element.get_attribute('name'),
            'class': await element.get_attribute('class'),
            'href': await element.get_attribute('href') if tag_name == 'a' else None,
            'placeholder': await element.get_attribute('placeholder'),
            'value': await element.get_attribute('value'),
            'title': await element.get_attribute('title'),
        }

        # Generate a CSS selector for the element
        css_selector = await self._generate_css_selector(element, element_info)
        element_info['css_selector'] = css_selector

        return {k: v for k, v in element_info.items() if v not in (None, '')}

    async def _generate_css_selector(self, element: ElementHandle, element_info: Dict[str, str]) -> str:
        """Generate a unique CSS selector for the element."""
        selectors = []

        # Use ID if available
        if element_info.get('id'):
            return f"#{element_info['id']}"

        # Start with tag name
        selector = element_info['tag']

        # Add classes
        if element_info.get('class'):
            classes = element_info['class'].split()
            selector += '.' + '.'.join(classes)

        # Add other attributes
        for attr in ['type', 'name', 'placeholder', 'role']:
            if element_info.get(attr):
                selector += f"[{attr}='{element_info[attr]}']"

        selectors.append(selector)

        # Add nth-of-type to differentiate between similar elements
        siblings = await element.evaluate("""el => {
            const siblings = Array.from(el.parentNode.children).filter(child => child.tagName === el.tagName);
            return siblings.indexOf(el) + 1;
        }""")
        selectors[-1] += f":nth-of-type({siblings})"

        # Construct the full selector
        full_selector = ' > '.join(selectors)

        # # Verify uniqueness
        # try:
        #     count = await self.page.locator(full_selector).count()
        #     if count > 1:
        #         logger.warning(
        #             f"Generated selector '{full_selector}' matches {count} elements. It may not be unique.")
        # except Exception as e:
        #     logger.error(
        #         f"Error verifying selector '{full_selector}': {str(e)}")
        #     # Fallback to a more general selector
        #     full_selector = f"{element_info['tag']}:nth-of-type({siblings})"

        return full_selector

    async def get_text(self) -> str:
        """Get the text content of the current page."""
        return await self.page.inner_text('body')

    def get_action_history(self) -> List[Tuple[str, str, Optional[str]]]:
        """Get the history of actions performed."""
        return self.action_history

    async def get_state(self, state_type: str = 'text') -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """
        Get the current state of the page.

        Args:
            state_type (str): The type of state to retrieve ('text', 'html', or 'interactive').

        Returns:
            Dict[str, Union[str, List[Dict[str, str]]]]: The current state.

        Raises:
            ValueError: If an unsupported state type is provided.
        """
        if state_type == 'text':
            state_content = await self.get_text()
        elif state_type == 'html':
            state_content = await self.get_html()
        elif state_type == 'interactive':
            state_content = await self.get_interactive_elements()
        else:
            raise ValueError(f"Unsupported state type: {state_type}")

        return {
            "content": state_content,
            "history": self.get_action_history()
        }

    def get_supported_actions(self) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        """Get a dictionary of supported actions and their descriptions."""
        return {
            "click": {"description": "Click on an element e.g., link, button or element with role button etc", "parameters": ["selector"]},
            "press": {"description": "Press a key on the keyboard. This can be used to submit a form e.g. pressing Enter on text input or textarea", "parameters": ["selector", "value"]},
            "type": {"description": "Type text into an input field specified by the selector", "parameters": ["selector", "value"]},
            "select": {"description": "Select an option from a dropdown specified by the selector", "parameters": ["selector", "value"]},
            "navigate": {"description": "Navigate to a new URL", "parameters": ["value"]},

        }

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if not self.is_initialized:
            logger.warning("Attempting to close an uninitialized WebBrowser.")
            return

        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during WebBrowser closure: {str(e)}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.is_initialized = False
            logger.info(
                "WebBrowser successfully closed and resources cleaned up.")
