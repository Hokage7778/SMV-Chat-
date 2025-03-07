import os
import re
import hashlib
import logging
from gtts import gTTS
from flask import current_app

logger = logging.getLogger(__name__)

def clean_text_for_tts(text):
    """Clean text for text-to-speech."""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Code
    text = re.sub(r'```.*?\n(.*?)```', r'\1', text, flags=re.DOTALL)  # Code blocks
    
    # Remove "Assistant:" prefix if present
    text = re.sub(r'^Assistant:\s*', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_cache_key(text, lang, slow):
    """Generate a unique cache key based on text content and TTS parameters."""
    # Create a string that includes all parameters that affect the audio output
    key_string = f"{text}_{lang}_{slow}"
    # Generate a hash of this string to use as the cache key
    return hashlib.md5(key_string.encode()).hexdigest()

def generate_tts(text, lang='en', speed=1.0):
    """
    Generate TTS audio using Google Text-to-Speech (gTTS).
    Returns the filename of the generated audio.
    """
    try:
        # Clean the text for TTS
        text = clean_text_for_tts(text)
        
        # Set slow parameter based on speed
        slow = speed < 0.9
        
        # Generate a cache key
        cache_key = get_cache_key(text, lang, slow)
        
        # Ensure cache directory exists
        app_static_folder = current_app.static_folder
        cache_dir = os.path.join(app_static_folder, 'audio', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Check if we already have this text cached
        cache_file = os.path.join(cache_dir, f"{cache_key}.mp3")
        if os.path.exists(cache_file):
            logger.info(f"Using cached TTS file: {cache_file}")
            return f"static/audio/cache/{cache_key}.mp3"
        
        # Breaking text into smaller chunks if too long
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 500:  # Reasonable chunk size
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        # If text is short enough, just use it directly
        if not chunks:
            chunks = [text]

        # Process only the first chunk for now to reduce latency
        text_to_process = chunks[0]

        # Create MP3 file with gTTS
        logger.info(f"Generating TTS for text: {text_to_process[:50]}...")
        tts = gTTS(text=text_to_process, lang=lang, slow=slow)
        tts.save(cache_file)
        
        logger.info(f"TTS file generated: {cache_file}")
        return f"static/audio/cache/{cache_key}.mp3"
        
    except Exception as e:
        logger.error(f"Error generating TTS: {e}", exc_info=True)
        return None 