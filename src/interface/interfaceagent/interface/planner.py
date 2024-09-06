from typing import List, Dict, Any, Optional
import json
from loguru import logger

from ..datamodel import BrowserAction
from .model import OpenAIPlannerModel
from .webbrowser import WebBrowser
from ..utils import parse_json


class Planner:
    def __init__(self, model: OpenAIPlannerModel, web_browser: WebBrowser, task: Optional[str] = None):
        """
        Initialize the Planner.

        Args:
            model (OpenAIPlannerModel): The language model for generating plans and actions.
            web_browser (WebBrowser): The web browser instance for executing actions.
            task (Optional[str]): The task to be accomplished.
        """
        self.model: OpenAIPlannerModel = model
        self.web_browser: WebBrowser = web_browser
        self.task: Optional[str] = task
        self.max_num_actions: int = 20
        self.action_count: int = 0
        self.highlevel_plan: List[str] = []
        self.max_retries: int = 3

    async def generate_plan(self) -> List[str]:
        """
        Generate a high-level plan for accomplishing the task.

        Returns:
            List[str]: A list of high-level steps to accomplish the task.
        """
        prompt = f"""
        You are a helpful assistant that can generate a broad high-level plan to accomplish a task using a web browser. 
        You can assume the browser is already open to the current page - {self.web_browser.page.url}.  
        E.g., to complete a task like "Find the contact information for a business", you might generate a plan like: 
        [
            "Search for the business name on Google", 
            "Navigate to the contact page",
            "Extract the contact information"
        ] 

        Now generate a plan to accomplish the following  
        Task: {self.task}

        Your response should be a perfect list of JSON strings with the following format:
        [ 
            "step 1", 
            "step 2",
            ...
        ]
        """
        response = self.model.generate(prompt)
        highlevel_plan = parse_json(response)
        logger.info(f"High-level plan: {highlevel_plan}")
        return highlevel_plan

    async def next_actions(self) -> List[Dict[str, Any]]:
        """
        Generate the next actions to execute based on the current state.

        Returns:
            List[Dict[str, Any]]: A list of actions to be executed.
        """

        if not self.web_browser.is_initialized:
            logger.info("WebBrowser not initialized. Initializing now.")
            await self.web_browser.initialize()
        supported_actions = self.web_browser.get_supported_actions()
        state = await self.web_browser.get_state(state_type='interactive')
        history = json.dumps(state['history'])
        prompt = f"""
        You are a helpful assistant and your goal is to generate actions that execute a particular step in a task using a browser. For example 

        You have access to a web browser with the following commands:
        {json.dumps(supported_actions, indent=2)}

        Task: {self.task} 
        Optional Highlevel Plan: {self.highlevel_plan}
        
        Browser action history: {history}
        Current URL: {self.web_browser.page.url}
        Current page elements: {state['content']}
        
        Given the overall task, current page content, and action history, Generate the next actions to execute. The action you generate must be based on a current page element above!

        Your response should be a perfect list of JSON objects with the following format:
        [
            {{
                "action": "",
                "selector": "", 
                "selector_type": "",
                "value": "",
                "url": ""
            }},
            ...
        ]

        A selection is a css selector that identifies the element to interact with. (e.g, 'a[href]', 'button', 'input', 'select', 'textarea', '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="menuitem"] etc). You MUST use all relevant information to generate the selector e.g. if tag, class, type or role is available use it e.g., 'input[type="text"]', 'a[href="https://example.com"]', etc. If you have to click an a tag and there is a full URL, just use the navigate action with the URL as the value. If the task involves search e.g. on google.com or bing.com, or any search box, the action should be to type the search query into the input element and press enter on the same element.
        """
        response = self.model.generate(prompt)
        next_actions = parse_json(response)
        logger.info(f"Next actions: {next_actions}")
        return next_actions

    async def check_task_complete(self) -> bool:
        """
        Check if the task has been completed.

        Returns:
            bool: True if the task is complete, False otherwise.
        """
        state = await self.web_browser.get_state()
        prompt = f"""
        Task: {self.task}
        Optional Highlevel Plan: {self.highlevel_plan}
        
        Browser action history: {json.dumps(state['history'])}
        Current URL: {self.web_browser.page.url}
        Current content: {state['content']}
        
        Is the task complete? Respond with a status (true or false) and a reason.
        You must provide a reason why you feel the current state of the task meets the requirements of teh task and rough high level plan. Your ressponse should be a formatted JSON object with a status and reason field.

        {{
            "status":  true/false,
            "reason": "..",
        }}

        """
        response = self.model.generate(prompt)
        response = parse_json(response)
        logger.info(f"Task complete: {response}")
        return response

    async def execute_action(self, action: Dict[str, Any] | BrowserAction) -> bool:
        """
        Execute a single action with retry logic.

        Args:
            action (Dict[str, Any] | BrowserAction): The action to be executed.

        Returns:
            bool: True if the action was executed successfully, False otherwise.
        """
        if isinstance(action, dict):
            action = BrowserAction(**action)

        logger.info(f"Executing: {action}")

        for attempt in range(self.max_retries):
            try:
                await self.web_browser.action(action)
                self.action_count += 1
                return True
            except Exception as e:
                logger.error(
                    f"Error executing action (attempt {attempt + 1}/{self.max_retries}): {e}, {action}")
                if attempt == self.max_retries - 1:
                    return False

        return False

    async def execute_plan(self) -> Dict[str, Any]:
        """
        Execute the plan to accomplish the task.

        Returns:
            Dict[str, Any]: A dictionary containing the task result and status information.
        """
        task_complete = False
        max_actions_reached = False

        while not task_complete and self.action_count < self.max_num_actions:
            try:
                next_actions = await self.next_actions()
                if not next_actions:
                    logger.warning(
                        "No more actions to execute. Task may be incomplete.")
                    break
                for action in next_actions:
                    success = await self.execute_action(action)
                    if not success:
                        logger.warning(
                            f"Failed to execute action after {self.max_retries} attempts. Attempting alternative action.")
                        alternative_action = await self.generate_alternative_action(action)
                        if alternative_action:
                            success = await self.execute_action(alternative_action)
                            if not success:
                                logger.warning(
                                    "Alternative action also failed.")
                    if self.action_count >= self.max_num_actions:
                        logger.warning(
                            f"Reached maximum number of actions ({self.max_num_actions}). Stopping execution.")
                        max_actions_reached = True
                        break
                if max_actions_reached:
                    break
            except Exception as e:
                logger.error(f"Error during planning: {e}", exc_info=True)
                break

            task_status = await self.check_task_complete()
            task_complete = task_status.get("status", False)

        result = {
            "task": self.task,
            "page_content": await self.web_browser.get_state(state_type='text'),
            "page_screenshot": await self.web_browser.screenshot(),
            "status": "completed" if task_complete else "incomplete",
            "completion_reason": (
                f"Reached maximum number of actions ({self.max_num_actions})"
                if max_actions_reached
                else task_status.get("reason", "Task could not be completed within the given constraints")
            )
        }

        logger.info("Task completed successfully!") if task_complete else logger.warning(
            result["completion_reason"])

        return result

    async def generate_alternative_action(self, failed_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate an alternative action when the original action fails.

        Args:
            failed_action (Dict[str, Any]): The action that failed to execute.

        Returns:
            Optional[Dict[str, Any]]: An alternative action, or None if no alternative could be generated.
        """
        prompt = f"""
        The following action failed:
        {json.dumps(failed_action)}

        Given the current task and page state, suggest an alternative action to achieve the same goal.
        Your response should be a single JSON object with the same format as the failed action.
        """
        response = self.model.generate(prompt)
        return parse_json(response)

    async def run(self, task: str) -> None:
        """
        Run the planner to accomplish the given task.

        Args:
            task (str): The task to be accomplished.
        """
        if not self.web_browser.is_initialized:
            logger.info("WebBrowser not initialized. Initializing now.")
            await self.web_browser.initialize()
        self.task = task

        try:
            self.highlevel_plan = await self.generate_plan()
            return await self.execute_plan()
        finally:
            await self.web_browser.close()
