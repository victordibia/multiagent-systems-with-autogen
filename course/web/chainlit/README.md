# Building a Multi-Agent Application with AutoGen and Chainlit

The AutoGen framework lets you built autonomous multi-agent applications. In this example, we will build a simple chat interface that interacts with an agent team built using the AutoGen AgentChat framework.

![AgentChat](public/chainlit_autogen.png)

## High-Level Description

The `app.py` script sets up a Chainlit chat interface that communicates with the AutoGen team. When a chat starts, it

- Initializes an AgentChat team and displays an Avatar.
- As users interact with the chat, their queries are sent to the team which responds.
- As agents respond/act, their responses are streamed back to the chat interface.

## Quickstart

To get started, ensure you have setup an API Key. We will be using the OpenAI API for this example.

1. Ensure you have an OPENAPI API key. Set this key in your environment variables as `OPENAI_API_KEY`.

2. Install the required Python packages by running:

```shell
pip install -r requirements.txt
```

3. Run the `app.py` script to start the Chainlit server.

```shell
chainlit run app.py
```

4. Interact with the Agent Team Chainlit interface.

### Function Definitions

- `start_chat`: Initializes the chat session and sets up the avatar for Claude.
- `run_team`: Sends the user's query to the Anthropic API and streams the response back to the chat interface.
- `chat`: Receives messages from the user and passes them to the `call_claude` function.

## Next Steps (Extra Credit)

In this example, we created a basic AutoGen team with a single agent, Claude. To extend this example, you can:
