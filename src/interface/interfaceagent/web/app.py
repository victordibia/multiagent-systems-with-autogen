from fastapi import FastAPI, Depends, HTTPException
from pydantic import AnyHttpUrl
from uuid import UUID
from interfaceagent.datamodel import WebRequestBrowserAction, WebResponse
from interfaceagent.interface import WebBrowser
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger

from interfaceagent.interface import WebBrowserManager

# Configure loguru
logger.add("api.log", rotation="500 MB", level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.browser_manager = WebBrowserManager()
    yield
    # Shutdown
    await app.state.browser_manager.close_all_sessions()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


async def get_browser_manager():
    return app.state.browser_manager


async def validate_session(
    session_id: UUID,
    browser_manager: WebBrowserManager = Depends(get_browser_manager)
) -> WebBrowser:
    browser = browser_manager.get_session(session_id)
    if not browser:
        raise HTTPException(status_code=404, detail="Invalid session ID")
    return browser


@app.post("/browser/session/create", response_model=WebResponse)
async def create_session(start_url: AnyHttpUrl, browser_manager: WebBrowserManager = Depends(get_browser_manager)):
    try:
        session_id = await browser_manager.create_session(start_url)
        return WebResponse(status=True, data={"session_id": session_id})
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return WebResponse(status=False, data={"error": "Failed to create session"})


@app.get("/browser/sessions", response_model=WebResponse)
async def list_sessions(browser_manager: WebBrowserManager = Depends(get_browser_manager)):
    try:
        sessions = browser_manager.list_sessions()
        return WebResponse(status=True, data={"sessions": sessions})
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        return WebResponse(status=False, data={"error": "Failed to list sessions"})


@app.post("/browser/session/{session_id}/action", response_model=WebResponse)
async def perform_action(
    action: WebRequestBrowserAction,
    browser: WebBrowser = Depends(validate_session)
):
    try:
        await browser.action(action.action, action.selector, action.value)
        return WebResponse(status=True, data={"message": "Action performed successfully"})
    except ValueError as e:
        logger.warning(f"Invalid action parameters: {str(e)}")
        return WebResponse(status=False, data={"error": str(e)})
    except Exception as e:
        logger.error(f"Error performing action: {str(e)}")
        return WebResponse(status=False, data={"error": "Failed to perform action"})


@app.get("/browser/session/{session_id}/state", response_model=WebResponse)
async def get_state(
    state_type: str = "text",
    browser: WebBrowser = Depends(validate_session)
):
    try:
        state = await browser.get_state(state_type)
        return WebResponse(status=True, data={"state": state})
    except ValueError as e:
        logger.warning(f"Invalid state type: {str(e)}")
        return WebResponse(status=False, data={"error": str(e)})
    except Exception as e:
        logger.error(f"Error getting state: {str(e)}")
        return WebResponse(status=False, data={"error": "Failed to get state"})


@app.post("/browser/session/{session_id}/close", response_model=WebResponse)
async def close_session(
    browser: WebBrowser = Depends(validate_session),
    browser_manager: WebBrowserManager = Depends(get_browser_manager)
):
    try:
        await browser_manager.close_session(browser.session_id)
        return WebResponse(status=True, data={"message": "Session closed successfully"})
    except Exception as e:
        logger.error(f"Error closing session: {str(e)}")
        return WebResponse(status=False, data={"error": "Failed to close session"})


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=WebResponse(status=False, data={
                            "error": "An unexpected error occurred. Please try again later."}).dict(),
    )
