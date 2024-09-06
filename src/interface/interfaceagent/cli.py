import typer
import uvicorn
import os
from typing_extensions import Annotated
# from llmx import providers

# from interfaceagent.web.backend.app import launch

app = typer.Typer()


@app.command()
def start(host: str = "127.0.0.1",
          port: int = 8082,
          workers: int = 1,
          reload: Annotated[bool, typer.Option("--reload")] = True,
          docs: bool = False):
    """
    Launch the interfaceagent .Pass in parameters host, port, workers, and reload to override the default values.
    """

    os.environ["interfaceagent_API_DOCS"] = str(docs)

    uvicorn.run(
        "interfaceagent.web.app:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.command()
def models():
    print("A list of supported providers:")


def run():
    app()


if __name__ == "__main__":
    app()
