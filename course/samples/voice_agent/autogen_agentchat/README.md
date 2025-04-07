# Voice-Enabled Agent Assistant

A Chainlit application that lets users speak to an AutoGen agent team and receive voice responses.

## Features

- **Voice Input**: Capture user speech with automatic silence detection (or just type)
- **Speech-to-Text**: Convert speech to text using OpenAI Whisper
- **Agent Processing**: Process requests with an AutoGen agent team
- **Text-to-Speech**: Convert responses back to speech using OpenAI TTS
- **Voice Customization**: Select from different voices and adjust speaking style

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your API keys:
   ```
   cp .env.example .env
   ```
4. Edit `.env` with your OpenAI API key

## Usage

1. Start the Chainlit application:
   ```
   chainlit run app.py
   ```
2. Open your browser at `http://localhost:8000`
3. Press `p` to start speaking or type your request
4. Adjust voice settings using the settings panel

## Project Structure

- `app.py`: Main Chainlit application
- `agent_team.py`: AutoGen team configuration
- `chainlit.md`: Chainlit welcome page

## Acknowledgements

- [Chainlit](https://github.com/Chainlit/chainlit)
- [AutoGen](https://github.com/microsoft/autogen)
- [OpenAI](https://github.com/openai/openai-python)
