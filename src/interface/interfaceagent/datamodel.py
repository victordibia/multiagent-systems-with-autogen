from typing import Any, Optional
from pydantic import BaseModel


class BrowserAction(BaseModel):
    action: str
    # e.g., 'a[href]', 'button', 'input', 'select', 'textarea', '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="menuitem"]'
    selector: Optional[str] = ""
    value: Optional[str] = None


class WebResponse(BaseModel):
    status: bool
    data: Optional[Any] = None


class WebRequestBrowserAction(BaseModel):
    action: str
    selector: Optional[str] = ""
    value: Optional[str] = None
