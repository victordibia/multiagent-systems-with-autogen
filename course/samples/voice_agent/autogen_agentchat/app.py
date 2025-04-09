# pip install -U chainlit 
# chainlit run app.py 
import os
import io
import wave
import numpy as np
import audioop
from typing import List, cast

import chainlit as cl
from openai import OpenAI, AsyncOpenAI
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage, BaseChatMessage
from autogen_agentchat.base import TaskResult, Team
from autogen_core import CancellationToken

# New import for input widgets in Chainlit
from chainlit.input_widget import Select, TextInput

# Import the team setup
from agent_team import create_agent_team 

# Initialize OpenAI clients
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
sync_client = OpenAI(api_key=OPENAI_API_KEY)

# Define silence detection parameters
SILENCE_THRESHOLD = 2000  # Adjust based on your audio level
SILENCE_TIMEOUT = 5000.0  # Seconds of silence to consider the turn finished

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    # Initialize session variables
    cl.user_session.set("message_history", [])
    cl.user_session.set("is_processing", False)
    
    # Set default TTS settings
    cl.user_session.set("tts_voice", "coral")
    cl.user_session.set("tts_instructions", "Speak in a clear and natural tone. You are ")
    
    # Create the agent team (with no tools for now)
    team = create_agent_team()
    cl.user_session.set("team", team)
    
    # Use ChatSettings for voice configuration - this is the modern approach
    settings = await cl.ChatSettings(
        [
            Select(
                id="voice-select",
                label="TTS Voice",
                values=["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"],
                initial_index=3  # coral is at index 3
            ),
            TextInput(
                id="voice-instructions",
                label="Voice Instructions",
                initial="Speak in a clear and natural tone.",
            )
        ]
    ).send()
    
    await cl.Message(
        content="Welcome! Press `p` to talk. You can customize the voice settings above."
    ).send()

@cl.on_settings_update
async def handle_settings_update(settings):
    """Handle settings updates from the UI."""
    if "voice-select" in settings:
        cl.user_session.set("tts_voice", settings["voice-select"])
    if "voice-instructions" in settings:
        cl.user_session.set("tts_instructions", settings["voice-instructions"])
    
    voice = settings.get("voice-select", cl.user_session.get("tts_voice", "coral"))
    await cl.Message(
        content=f"Voice settings updated: Using {voice} voice."
    ).send()

@cl.step(type="tool")
async def speech_to_text(audio_file):
    """Convert speech to text using OpenAI's API with streaming."""
    # Create a message that will be updated with streaming content
    msg = cl.Message(content="🎤 Transcribing your audio...", author="System")
    await msg.send()
    
    # Use the streaming option for transcription
    try:
        response = await openai_client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe", 
            file=audio_file,
            response_format="text"
        )
        
        # Update the message with the complete transcript
        transcript = response
        msg.content = f"✅ Transcription complete!"
        await msg.update()
        
        return transcript
    except Exception as e:
        msg.content = f"❌ Error in transcription: {str(e)}"
        await msg.update()
        return None

@cl.step(type="tool")
async def summarize_content(text: str, status_msg):
    """Summarize content to make it suitable for voice output."""
    if text is None:
        print("Error: text is None in summarize_content")
        return ""
        
    try:
        # Update status message
        status_msg.content = "✅ Task complete! Now summarizing for voice output..."
        await status_msg.update()
        
        # Use OpenAI client to summarize the content
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are a helpful assistant, your task is to summarize result of a task trace 
                    which have been assembled by a group of diligent agents. 
                    
                    The summary will be used to generate a voice message for the user. The summary 
                    must be written as a clear independent answer to the task e.g., it should not 
                    narrate the task, intermediate steps etc - a coherent informative answer that 
                    competent human would naturally provide, given the task and the result trace.
                    
                    Keep the summary concise and voice-friendly.
                    """
                },
                {
                    "role": "user",
                    "content": f"Please summarize the following text for voice output: {text}"
                }
            ]
        )
        
        summary = response.choices[0].message.content
        # Ensure we don't return None
        return summary if summary is not None else text
    except Exception as e:
        print(f"Error in summarization: {str(e)}")
        # Return the original text as fallback if summarization fails
        return text if text is not None else ""

@cl.step(type="tool")
async def text_to_speech(text: str, status_msg):
    """Convert text to speech using OpenAI's API with streaming."""
    # Validate input
    if not text:
        status_msg.content = "❌ Error: Cannot generate audio from empty text"
        await status_msg.update()
        return None
        
    # Update status message
    status_msg.content = "🔊 Generating audio response..."
    await status_msg.update()
    
    voice = cl.user_session.get("tts_voice") or "coral"
    instructions = cl.user_session.get("tts_instructions") or "Speak in a clear and natural tone."
    
    try:
        # Use the async client with streaming
        async with openai_client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            instructions=instructions,
            response_format="mp3",  # For better compatibility
        ) as response:
            # Create a buffer to store the audio
            buffer = io.BytesIO()
            
            # Stream the chunks to the buffer
            async for chunk in response.iter_bytes():
                if chunk:
                    buffer.write(chunk)
            
            # Reset buffer position
            buffer.seek(0)
            
            # Final status update
            status_msg.content = "✅ Processing complete!"
            await status_msg.update()
            
            return buffer.read()
    except Exception as e:
        print(f"Error in text to speech streaming: {str(e)}")
        status_msg.content = f"❌ Error generating audio: {str(e)}"
        await status_msg.update()
        return None

@cl.on_audio_start
async def on_audio_start():
    """Initialize audio capture session."""
    if cl.user_session.get("is_processing"):
        return False  # Don't start a new recording if we're processing
    
    cl.user_session.set("silent_duration_ms", 0)
    cl.user_session.set("is_speaking", False)
    cl.user_session.set("audio_chunks", [])
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Process incoming audio chunks and detect silence."""
    audio_chunks = cl.user_session.get("audio_chunks")

    if audio_chunks is not None:
        audio_chunk = np.frombuffer(chunk.data, dtype=np.int16)
        audio_chunks.append(audio_chunk)

    # If this is the first chunk, initialize timers and state
    if chunk.isStart:
        cl.user_session.set("last_elapsed_time", chunk.elapsedTime)
        cl.user_session.set("is_speaking", True)
        return

    audio_chunks = cl.user_session.get("audio_chunks")
    last_elapsed_time = cl.user_session.get("last_elapsed_time") or 0
    silent_duration_ms = cl.user_session.get("silent_duration_ms") or 0
    is_speaking = cl.user_session.get("is_speaking")

    # Calculate the time difference between this chunk and the previous one
    time_diff_ms: float = chunk.elapsedTime - last_elapsed_time
    cl.user_session.set("last_elapsed_time", chunk.elapsedTime)

    # Compute the RMS energy of the audio chunk
    audio_energy = audioop.rms(chunk.data, 2)

    if audio_energy < SILENCE_THRESHOLD:
        # Audio is considered silent
        silent_duration_ms += time_diff_ms
        cl.user_session.set("silent_duration_ms", silent_duration_ms)
        if silent_duration_ms >= SILENCE_TIMEOUT and is_speaking:
            cl.user_session.set("is_speaking", False)
            await process_audio()
    else:
        # Audio is not silent, reset silence timer and mark as speaking
        cl.user_session.set("silent_duration_ms", 0)
        if not is_speaking:
            cl.user_session.set("is_speaking", True)

async def process_audio():
    """Process the recorded audio after silence is detected."""
    # Mark that we're processing to prevent new recordings
    cl.user_session.set("is_processing", True)
    
    # Get the audio buffer from the session
    if audio_chunks := cl.user_session.get("audio_chunks"):
        # Concatenate all chunks
        concatenated = np.concatenate(list(audio_chunks))

        # Create an in-memory binary stream
        wav_buffer = io.BytesIO()

        # Create WAV file with proper parameters
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(24000)  # sample rate (24kHz PCM)
            wav_file.writeframes(concatenated.tobytes())

        # Reset buffer position
        wav_buffer.seek(0)

        # Reset session audio buffer
        cl.user_session.set("audio_chunks", [])

        # Check audio duration
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
        
        if duration <= 1.0:
            await cl.Message(content="The audio is too short, please try again.").send()
            cl.user_session.set("is_processing", False)
            return

        # Convert audio to proper format for API
        audio_buffer = wav_buffer.getvalue()
        audio_element = cl.Audio(content=audio_buffer, mime="audio/wav")

        # Create a tuple for the audio file (similar to a file upload)
        whisper_input = ("audio.wav", audio_buffer, "audio/wav")
        
        # Play "processing" confirmation - use async client for streaming
        confirmation_text = "Got it. I'm processing your request."
        # Use the same text_to_speech function but with a temporary status message
        temp_status = cl.Message(content="Preparing...", author="System")
        await temp_status.send()
        confirmation_audio = await text_to_speech(confirmation_text, temp_status)

        # Send as a separate message so it doesn't get interrupted
        if confirmation_audio:
            await cl.Message(
                content="",
                elements=[cl.Audio(auto_play=True, mime="audio/mp3", content=confirmation_audio)]
            ).send()

        # Create the main status message for updates
        status_msg = cl.Message(content="🎧 Processing your request...", author="System")
        await status_msg.send()
        
        # Transcribe the audio
        transcription = await speech_to_text(whisper_input)
        if not transcription:
            cl.user_session.set("is_processing", False)
            return

        # Send the transcribed message to the UI
        await cl.Message(
            author="You",
            type="user_message",
            content=transcription,
            elements=[audio_element],
        ).send()

        # Update status message for agent processing
        status_msg.content = "🧠 Agents working on your request..."
        await status_msg.update()

        # Process with agent team
        await process_with_team(transcription, status_msg)
        
        # Reset processing flag
        cl.user_session.set("is_processing", False)

async def process_with_team(transcription, status_msg):
    """Process the transcription with the agent team."""
    team = cast(Team,cl.user_session.get("team"))
    
    # Streaming response message
    streaming_response = None
    
    task_result = ""
    
    # Stream the messages from the team
    async for msg in team.run_stream(
        task=[TextMessage(content=transcription, source="user")],
        cancellation_token=CancellationToken(),
    ):
        if  isinstance(msg, BaseChatMessage):
            if msg.source == "user":
                continue
            await cl.Message(
                content= msg.source + ":" + msg.to_text(),
                author=msg.source
            ).send()

        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user
            if streaming_response is None:
                # Start a new streaming response
                streaming_response = cl.Message(content=msg.source + ": ", author=msg.source)
                await streaming_response.send()
            await streaming_response.stream_token(msg.content) 
            
             
        elif streaming_response is not None:
            # Complete the streaming response
            streaming_response = None
        
        elif isinstance(msg, TaskResult):
            # Send the task termination message
            final_message = "Task completed."
            task_result = str(msg)
            if msg.stop_reason:
                final_message += f" Reason: {msg.stop_reason}"
            await cl.Message(content=final_message).send()
    
    # Generate the final response for TTS
    
    # Add summarization step before text-to-speech
    summarized_text = await summarize_content(task_result, status_msg)
    
    # Check if summarized_text is None before proceeding
    if summarized_text is None:
        status_msg.content = "❌ Summarization failed. Using original response instead."
        await status_msg.update()
        summarized_text = task_result or "Sorry, I couldn't process your request properly."
    
    # Convert summarized text to speech
    tts_audio = await text_to_speech(summarized_text, status_msg)
    if tts_audio:
        audio_element = cl.Audio(auto_play=True, mime="audio/mp3", content=tts_audio)
        await cl.Message(content=summarized_text, elements=[audio_element]).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages from the user."""
    if cl.user_session.get("is_processing"):
        await cl.Message(content="I'm still processing your previous request. Please wait.").send()
        return
    
    # Create a status message that will be updated throughout the process
    status_msg = cl.Message(content="🎧 Processing your request...", author="System")
    await status_msg.send()
    
    # Update status message for agent processing
    status_msg.content = "🧠 Agents working on your request..."
    await status_msg.update()
    
    # Process the text message with the agent team
    await process_with_team(message.content, status_msg)


@cl.set_starters
async def set_starters(user_or_none: cl.User | None) -> List[cl.Starter]:
    """Set starter messages for the chat."""
    return [
        cl.Starter(
            label="Tell me about the weather",
            message="Tell me about the weather today",
        ),
        cl.Starter(
            label="Generate a poem",
            message="Write a short poem about artificial intelligence",
        ),
        cl.Starter(
            label="Explain a concept",
            message="Explain how neural networks work in simple terms",
        ),
    ]


if __name__ == "__main__":
    # Run the Chainlit app
    print("Please run this script using Chainlit.")