import os
import sys
import time
import json
import re
import hashlib
import threading
import queue
import subprocess
import tempfile
import logging
import requests
from datetime import date
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from gtts import gTTS
from dotenv import load_dotenv
from typing import Dict, List
import datetime

# Load environment variables
load_dotenv()

# Configure logging FIRST, before any potential usage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Create a named logger that can be imported elsewhere
logger = logging.getLogger(__name__)

# Try to import speech_recognition, but provide a fallback
SPEECH_RECOGNITION_AVAILABLE = False
SPEECH_RECOGNITION_ERROR = "Module not installed"

try:
    # Check if aifc module is available without importing it directly
    aifc_available = False
    try:
        # Try to import a module that depends on aifc
        import importlib.util
        aifc_spec = importlib.util.find_spec('aifc')
        aifc_available = aifc_spec is not None
        
        if aifc_available:
            logger.info("aifc module is available.")
        else:
            logger.error("aifc module is not available. This is required by speech_recognition.")
            SPEECH_RECOGNITION_ERROR = "Missing aifc module (required dependency)"
    except Exception as e:
        logger.error(f"Error checking for aifc module: {e}")
        SPEECH_RECOGNITION_ERROR = "Error checking for required dependencies"
    
    # Only try to import speech_recognition if aifc is available
    if aifc_available:
        import speech_recognition as sr
        # Test if we can create a recognizer to confirm the module is working
        test_recognizer = sr.Recognizer()
        SPEECH_RECOGNITION_AVAILABLE = True
        logger.info("Speech recognition module successfully imported and initialized.")
except ImportError as e:
    logger.warning(f"speech_recognition module could not be imported: {e}. Speech-to-text functionality will be disabled.")
    SPEECH_RECOGNITION_ERROR = f"Import error: {str(e)}"
except Exception as e:
    logger.warning(f"Error initializing speech recognition: {e}. Speech-to-text functionality will be disabled.")
    SPEECH_RECOGNITION_ERROR = f"Initialization error: {str(e)}"

# Initialize Flask app directly
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['SECRET_KEY'] = 'your-secret-key'

# Ensure necessary directories exist
os.makedirs(os.path.join(app.static_folder, 'audio', 'cache'), exist_ok=True)

# ----- Configuration for APIs -----
# Google API Key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', "AIzaSyDuH-mIR0us2wUCbvH79xXQZSukDwwo-jk")

# TomTom API Key
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY', "n0iAXNs9HZyBNXupJL3xQUeA96jlOgXJ")

# OpenStreetMap Configuration
OPENSTREETMAP_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENSTREETMAP_USER_AGENT = "E-RickshawAssistant/1.0"  # Required by OSM Nominatim API

# Initialize Google Generative AI with API key
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("Successfully configured Google Generative AI client")
    
    # Test the configuration by creating a simple model
    test_model = genai.GenerativeModel("gemini-2.0-flash")
    logger.info("Successfully created test model")
    
    # Self-test the Gemini API configuration
    def test_gemini_api():
        try:
            # Use gemini-1.5-flash model for testing
            test_model = genai.GenerativeModel("gemini-1.5-flash")
            test_response = test_model.generate_content("Respond with 'API working' if you can read this.")
            
            if test_response and test_response.text and "API working" in test_response.text:
                logger.info("✅ Gemini API self-test successful")
                return True
            else:
                logger.error("❌ Gemini API self-test failed: Unexpected response")
                return False
        except Exception as e:
            logger.error(f"❌ Gemini API self-test failed with error: {e}")
            return False

    # Run the self-test
    gemini_api_working = test_gemini_api()
    
except Exception as e:
    logger.error(f"Error configuring Google Generative AI: {e}")
    print(f"API KEY CONFIGURATION ERROR: {e}")

# Generation configuration for the model
GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}

# ----- Conversation Setup -----
conversation_history = {}  # Dictionary to store conversation history for each session
today = str(date.today())

# ----- Global Variables -----
tts_queue = queue.Queue()
tts_cache = {}  # Cache for TTS audio files

# ----- Map API Functions -----
def geocode_with_openstreetmap(query):
    """
    Geocode an address or location name using OpenStreetMap's Nominatim API.
    Returns location data including coordinates.
    """
    try:
        headers = {
            'User-Agent': OPENSTREETMAP_USER_AGENT
        }
        
        params = {
            'q': query,
            'format': 'json',
            'limit': 1
        }
        
        logger.info(f"Sending geocoding request to OpenStreetMap for query: {query}")
        response = requests.get(
            OPENSTREETMAP_NOMINATIM_URL,
            params=params,
            headers=headers
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # Extract relevant information
                location = data[0]
                result = {
                    'lat': float(location.get('lat')),
                    'lon': float(location.get('lon')),
                    'display_name': location.get('display_name'),
                    'type': location.get('type'),
                    'importance': location.get('importance')
                }
                logger.info(f"OpenStreetMap geocoding successful: {result}")
                return result
            else:
                logger.warning(f"No results found for query: {query}")
                return None
        else:
            logger.error(f"OpenStreetMap API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error in OpenStreetMap geocoding: {e}")
        return None

def search_with_tomtom(query, lat=None, lon=None):
    """
    Search for places using TomTom's Search API.
    Can search by query string or by coordinates.
    """
    if not TOMTOM_API_KEY:
        logger.error("TomTom API key is not configured")
        return None
        
    try:
        base_url = "https://api.tomtom.com/search/2/search"
        
        params = {
            'key': TOMTOM_API_KEY,
            'limit': 10,
            'language': 'en-US'
        }
        
        # If coordinates are provided, add them to the search
        if lat is not None and lon is not None:
            params['lat'] = lat
            params['lon'] = lon
        
        # Construct the URL with the query
        url = f"{base_url}/{query}.json"
        
        logger.info(f"Sending search request to TomTom API for query: {query}")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                # Process and return the results
                processed_results = []
                for result in results:
                    poi = result.get('poi', {})
                    address = result.get('address', {})
                    position = result.get('position', {})
                    
                    processed_results.append({
                        'name': poi.get('name'),
                        'category': poi.get('categorySet', [{}])[0].get('name') if poi.get('categorySet') else None,
                        'address': address.get('freeformAddress'),
                        'lat': position.get('lat'),
                        'lon': position.get('lon'),
                        'distance': result.get('dist')  # Distance in meters if lat/lon was provided
                    })
                
                logger.info(f"TomTom search successful, found {len(processed_results)} results")
                return processed_results
            else:
                logger.warning(f"No results found for TomTom search: {query}")
                return []
        else:
            logger.error(f"TomTom API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error in TomTom search: {e}")
        return None

def get_route_with_tomtom(start_lat, start_lon, end_lat, end_lon, mode='car'):
    """
    Get routing information between two points using TomTom's Routing API.
    
    Args:
        start_lat: Starting point latitude
        start_lon: Starting point longitude
        end_lat: Ending point latitude
        end_lon: Ending point longitude
        mode: Transportation mode (car, pedestrian, bicycle)
        
    Returns:
        Dictionary with route information or None if request failed
    """
    if not TOMTOM_API_KEY:
        logger.error("TomTom API key is not configured")
        return None
        
    try:
        base_url = "https://api.tomtom.com/routing/1/calculateRoute"
        
        # Construct the coordinates part of the URL
        coordinates = f"{start_lat},{start_lon}:{end_lat},{end_lon}"
        
        # Set up the parameters
        params = {
            'key': TOMTOM_API_KEY,
            'travelMode': mode,
            'traffic': 'true',
            'instructionsType': 'text',
            'language': 'en-US'
        }
        
        # Construct the full URL
        url = f"{base_url}/{coordinates}/json"
        
        logger.info(f"Sending routing request to TomTom API from {start_lat},{start_lon} to {end_lat},{end_lon}")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            routes = data.get('routes', [])
            
            if routes:
                route = routes[0]  # Get the first (best) route
                summary = route.get('summary', {})
                
                # Extract the relevant information
                result = {
                    'distance_meters': summary.get('lengthInMeters'),
                    'travel_time_seconds': summary.get('travelTimeInSeconds'),
                    'traffic_delay_seconds': summary.get('trafficDelayInSeconds', 0),
                    'instructions': []
                }
                
                # Extract turn-by-turn instructions
                for leg in route.get('legs', []):
                    for instruction in leg.get('instructions', []):
                        result['instructions'].append({
                            'instruction': instruction.get('message'),
                            'distance_meters': instruction.get('routeOffsetInMeters'),
                            'travel_time_seconds': instruction.get('travelTimeInSeconds')
                        })
                
                logger.info(f"TomTom routing successful, route is {result['distance_meters']} meters")
                return result
            else:
                logger.warning("No routes found")
                return None
        else:
            logger.error(f"TomTom Routing API error: {response.status_code}, {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error in TomTom routing: {e}")
        return None

# ----- Other Functions -----
def get_session_history(session_id):
    """Get or initialize conversation history for a session."""
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": """You are SMV's specialized E-rickshaw Assistant, focused exclusively on helping drivers with their e-rickshaw related queries. 

Key Guidelines:
1. ONLY answer questions related to:
   - E-rickshaw operation, maintenance, and troubleshooting
   - Battery issues and charging
   - Vehicle performance and mileage
   - Dashboard information
   - Service and maintenance schedules
   - Safety guidelines
   - SMV support and contact information

2. For non-e-rickshaw queries:
   - Politely inform that you can only assist with e-rickshaw related questions
   - Example: "I apologize, but I can only assist with questions related to your e-rickshaw, its maintenance, or dashboard information. Please feel free to ask any e-rickshaw related questions."

3. Access Dashboard Data:
   When responding, always check and include relevant dashboard information:
   - Current battery percentage
   - Vehicle number
   - Last service date
   - Next service date
   - Driver rating
   - Current location

4. Battery Issues Response Format:
   a) Acknowledge the issue
   b) Check dashboard battery status
   c) Provide specific troubleshooting steps
   d) Include safety warnings if applicable
   e) ALWAYS end with: "For more detailed assistance, please contact your SMV representative at [contact number]"

5. Standard Response Structure:
   a) Reference relevant dashboard data
   b) Provide specific, actionable advice
   c) Include safety precautions if applicable
   d) End with SMV contact information

6. Emergency Situations:
   For critical issues (smoke, unusual sounds, battery damage):
   - Advise to stop vehicle immediately
   - Provide emergency safety steps
   - Emphasize contacting SMV representative urgently

7. Maintenance Queries:
   - Check service history from dashboard
   - Provide maintenance schedule
   - Include basic maintenance tips
   - Remind about next service date

Example Responses:

For Battery Issues:
"I see your battery is currently at [dashboard_battery]%. Based on the dashboard data:
1. Specific issue addressing
2. Troubleshooting steps
3. Safety precautions
For more detailed assistance, please contact your SMV representative at [contact_number]"

For Maintenance Queries:
"According to your dashboard:
- Last service: [dashboard_last_service]
- Next service: [dashboard_next_service]
[Specific maintenance advice]
For more information, please contact your SMV representative at [contact_number]"

For Performance Issues:
"Based on your current metrics:
- Battery: [dashboard_battery]%
- Driving Rating: [dashboard_rating]
[Specific performance advice]
For detailed assistance, please contact your SMV representative at [contact_number]"

Remember:
- Always be professional and supportive
- Focus on safety first
- Include relevant dashboard data
- End every response with SMV contact information
- Only address e-rickshaw related queries."""}
        ]
    return conversation_history[session_id]

def check_ffmpeg_available():
    """Check if ffmpeg is available on the system."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("FFmpeg is not available. Audio conversion will not work.")
        return False

def convert_webm_to_wav(webm_file):
    """Convert WebM audio file to WAV format using ffmpeg."""
    try:
        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wav_file = temp_wav.name
        
        logger.info(f"Converting WebM file {webm_file} to WAV format {wav_file}")
        
        # Use ffmpeg to convert WebM to WAV
        process = subprocess.run(
            ['ffmpeg', '-i', webm_file, '-ar', '16000', '-ac', '1', '-y', wav_file], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        )
        
        logger.info(f"Conversion completed successfully")
        return wav_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting WebM to WAV: {e}")
        logger.error(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No error output'}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in conversion: {e}")
        return None

def direct_transcribe_audio(audio_file):
    """
    Transcribe audio using Google's Speech-to-Text API directly, without using the speech_recognition library.
    This is a fallback method when the speech_recognition library is not available.
    
    Args:
        audio_file: Path to the WAV audio file
        
    Returns:
        Transcribed text or None if transcription failed
    """
    try:
        # Check if we have the Google API key
        if not GOOGLE_API_KEY:
            logger.error("Google API key is not configured")
            return None
            
        # Use Google's Generative AI API for transcription
        # First, convert the audio file to base64
        with open(audio_file, 'rb') as f:
            audio_content = f.read()
        
        import base64
        audio_b64 = base64.b64encode(audio_content).decode('utf-8')
        
        # Create a model instance
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Send the audio to the model with a prompt to transcribe it
        response = model.generate_content([
            "Please transcribe the following audio accurately. Just return the transcription text without any additional commentary.",
            {"mime_type": "audio/wav", "data": audio_b64}
        ])
        
        # Extract the transcription from the response
        if response and response.text:
            transcription = response.text.strip()
            logger.info(f"Direct transcription result: {transcription}")
            return transcription
        else:
            logger.warning("No transcription result from Google API")
            return None
            
    except Exception as e:
        logger.error(f"Error in direct transcription: {e}", exc_info=True)
        return None

def transcribe_audio_with_google_api(audio_file):
    """
    Use Google's Speech Recognition API to transcribe audio.
    """
    if not SPEECH_RECOGNITION_AVAILABLE:
        logger.warning("Speech recognition is not available")
        return None
    
    try:
        logger.info(f"Transcribing audio file: {audio_file}")
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
        
        logger.info("Sending audio to Google Speech Recognition API")
        text = recognizer.recognize_google(audio_data)
        logger.info(f"Transcription result: {text}")
        return text
    except sr.UnknownValueError:
        logger.warning("Google Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google Speech Recognition service: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
        return None

def chat_with_google(prompt, session_id):
    """
    Append user's prompt to conversation history and generate a response
    using Google Generative AI.
    """
    history = get_session_history(session_id)
    history.append({"role": "user", "content": prompt})
    
    full_prompt = "\n".join(
        [f'{msg["role"].capitalize()}: {msg["content"]}' for msg in history]
    )

    model = genai.GenerativeModel("gemini-1.5-flash", generation_config=GENERATION_CONFIG)
    response = model.generate_content(full_prompt)
    reply = response.text if response.text else ""

    history.append({"role": "assistant", "content": reply})
    return reply.strip()

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

def clean_text_for_display(text):
    """Clean text for display in the UI, removing markdown formatting."""
    # Remove asterisks used for bold/italic in markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    
    # Remove other markdown formatting
    text = re.sub(r'__(.*?)__', r'\1', text)      # Underline
    text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
    
    # Clean up any double spaces that might result
    text = re.sub(r'\s+', ' ', text)
    
    return text

def get_cache_key(text, lang, slow):
    """Generate a unique cache key based on text content and TTS parameters."""
    # Create a string that includes all parameters that affect the audio output
    key_string = f"{text}_{lang}_{slow}"
    # Generate a hash of this string to use as the cache key
    return hashlib.md5(key_string.encode()).hexdigest()

def google_tts(text, lang='en', slow=False, speed=1.0):
    """
    Generate TTS audio using Google Text-to-Speech (gTTS).
    Returns the filename of the generated audio or None if an error occurs.
    """
    try:
        # Clean the text for TTS
        text = clean_text_for_tts(text)
        
        # Generate a cache key
        cache_key = get_cache_key(text, lang, slow)
        cache_dir = os.path.join(app.static_folder, 'audio', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Check if we already have this text cached
        cache_file = os.path.join(cache_dir, f"{cache_key}.mp3")
        if os.path.exists(cache_file):
            logger.info(f"Using cached audio file: {cache_file}")
            return f"audio/cache/{cache_key}.mp3"
        
        # If text is too long, take just the first part
        max_length = 1000
        if len(text) > max_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_length}")
            text = text[:max_length] + "..."
        
        # Create MP3 file with gTTS
        logger.info(f"Generating new TTS audio for text: {text[:50]}...")
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(cache_file)
        
        # Apply speed adjustment if needed
        if speed != 1.0:
            process_audio_speed(cache_file, speed)
            
        return f"audio/cache/{cache_key}.mp3"
    except Exception as e:
        logger.error(f"Error in google_tts: {e}", exc_info=True)
        return None

def append_to_log(session_id, text):
    """Append text to a daily log file."""
    log_filename = f"chatlog-{today}.txt"
    with open(log_filename, "a") as f:
        f.write(f"Session {session_id}: {text}\n")

def process_audio_speed(audio_path, speed):
    """
    Process audio file to change its speed.
    
    Args:
        audio_path: Path to the audio file
        speed: Speed factor (1.0 is normal speed)
    """
    try:
        # Create a temporary file for the processed audio
        temp_path = audio_path + ".temp.mp3"
        
        # Use ffmpeg to change the audio speed
        subprocess.run([
            'ffmpeg', '-i', audio_path, 
            '-filter:a', f'atempo={speed}', 
            '-y', temp_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Replace the original file with the processed one
        os.replace(temp_path, audio_path)
        logger.info(f"Audio speed processed: {audio_path}, speed: {speed}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing audio speed: {e}")
        logger.error(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No error output'}")
        # If there's an error, we'll just use the original audio file
    except Exception as e:
        logger.error(f"Error processing audio speed: {e}")
        # If there's an error, we'll just use the original audio file

# ----- Routes -----
@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/test-logo')
def test_logo():
    return render_template('test_logo.html')

# New class to manage chatbot state and interactions
class SMVChatbot:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.conversations: Dict[str, genai.ChatSession] = {}
        
    def get_dashboard_data(self) -> dict:
        """Get real-time dashboard data"""
        return {
            "battery_percentage": "93",
            "vehicle_number": "UP32 BZ 5678",
            "last_service": "10 June 2024",
            "next_service": "10 December 2025",
            "driver_rating": "4.2",
            "current_location": "Lucknow, Uttar Pradesh, 226014, India"
        }

    def get_system_prompt(self, dashboard_data: dict) -> str:
        """Generate system prompt with current data"""
        return f"""You are an AI assistant specifically designed for SMV e-rickshaw drivers. You must ALWAYS:

1. Start EVERY response with "Namaste! I am your SMV e-rickshaw assistant."

2. CURRENT DASHBOARD STATUS:
   - Battery: {dashboard_data['battery_percentage']}%
   - Vehicle: {dashboard_data['vehicle_number']}
   - Last Service: {dashboard_data['last_service']}
   - Next Service: {dashboard_data['next_service']}
   - Driver Rating: {dashboard_data['driver_rating']}

3. RESPONSE RULES:
   - ONLY answer questions about e-rickshaws, maintenance, battery, or dashboard
   - Include relevant dashboard data in EVERY response
   - Add safety warnings when discussing technical issues
   - End EVERY response with "For immediate assistance, contact SMV support at 1800-XXX-XXXX"

4. For BATTERY ISSUES:
   - First state current battery level
   - List specific troubleshooting steps
   - Include charging safety warnings
   - Mention if service check needed

5. For MAINTENANCE QUERIES:
   - Reference last service date
   - State next service date
   - Provide specific maintenance tips

6. For NON-E-RICKSHAW questions:
   Respond ONLY with: "I am specialized in e-rickshaw support. Please ask me about your e-rickshaw, its maintenance, battery, or dashboard information."

7. SAFETY FIRST:
   For any critical issues (smoke, damage, unusual sounds):
   - Advise to stop vehicle immediately
   - Provide emergency steps
   - Emphasize contacting SMV support urgently"""

    def get_chat_session(self, session_id: str) -> genai.ChatSession:
        """Get or create a chat session for the user"""
        if session_id not in self.conversations:
            chat = self.model.start_chat(history=[])
            dashboard_data = self.get_dashboard_data()
            system_prompt = self.get_system_prompt(dashboard_data)
            chat.send_message(system_prompt)
            self.conversations[session_id] = chat
        return self.conversations[session_id]

    def handle_message(self, message: str, session_id: str) -> str:
        """Process a message and return the response"""
        try:
            chat = self.get_chat_session(session_id)
            
            # Enhance user message with context
            dashboard_data = self.get_dashboard_data()
            enhanced_message = f"""User Query: {message}

Current Dashboard Status:
- Battery: {dashboard_data['battery_percentage']}%
- Vehicle: {dashboard_data['vehicle_number']}
- Last Service: {dashboard_data['last_service']}
- Next Service: {dashboard_data['next_service']}

Please provide a helpful response following the system prompt guidelines."""

            response = chat.send_message(enhanced_message)
            return response.text if response.text else "I apologize, I'm having trouble responding. Please try again."
            
        except Exception as e:
            logger.error(f"Error in chat handling: {e}")
            return "I apologize, I'm having technical difficulties. Please try again."

# Initialize the chatbot
smv_chatbot = SMVChatbot()

# Update the chat endpoint
@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat."""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    language = data.get('language', 'en')
    speed = float(data.get('speed', 1.0))
    
    try:
        # Log the request details for debugging
        logger.info(f"Chat endpoint called with message: '{message}', session_id: {session_id}")
        
        # Dashboard data
        dashboard = {
            "battery_percentage": "93",
            "vehicle_number": "UP32 BZ 5678",
            "last_service": "10 June 2024",
            "next_service": "10 December 2024",
            "driver_rating": "4.5",
            "location": "Lucknow, Uttar Pradesh"
        }
        
        # Get nearby places data from the map
        nearby_places = {
            "schools": [
                {"name": "APS Academy", "distance": "1.1 km"},
                {"name": "City Montessori School", "distance": "2.3 km"}
            ],
            "bus_stations": [
                {"name": "Central Bus Terminal", "distance": "0.7 km"},
                {"name": "Charbagh Bus Station", "distance": "3.5 km"}
            ],
            "malls": [
                {"name": "City Center Mall", "distance": "1.5 km"},
                {"name": "Phoenix Palassio", "distance": "4.2 km"}
            ]
        }
        
        # Check if this is the first message in the session
        is_first_message = session_id not in conversation_history or len(conversation_history.get(session_id, [])) <= 1
        
        # Create a new model instance for each request with explicit configuration
        try:
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config=generation_config
            )
            logger.info("Successfully created Gemini model instance")
            
            # Completely revised prompt with better instructions for professional responses
            prompt = f"""You are the SMV E-rickshaw Assistant, a professional and helpful AI assistant for e-rickshaw drivers.

CORE PRINCIPLES:
1. Maintain a professional, helpful tone at all times
2. Only answer questions about e-rickshaws, maintenance, battery, dashboard, or nearby locations
3. For non-e-rickshaw questions, politely redirect to e-rickshaw topics
4. Only suggest contacting the SMV team (1800-XXX-XXXX) for serious technical issues that cannot be resolved with advice
5. Provide specific, actionable information when possible

DASHBOARD DATA (ONLY mention when DIRECTLY relevant and NECESSARY for answering the specific question):
- Battery: {dashboard['battery_percentage']}%
- Vehicle: {dashboard['vehicle_number']}
- Last Service: {dashboard['last_service']}
- Next Service: {dashboard['next_service']}
- Driver Rating: {dashboard['driver_rating']}
- Location: {dashboard['location']}

NEARBY PLACES (ONLY for location-related questions):
- Schools: {', '.join([f"{school['name']} ({school['distance']})" for school in nearby_places['schools']])}
- Bus Stations: {', '.join([f"{station['name']} ({station['distance']})" for station in nearby_places['bus_stations']])}
- Malls: {', '.join([f"{mall['name']} ({mall['distance']})" for mall in nearby_places['malls']])}

RESPONSE GUIDELINES:
- For greetings: Respond professionally without mentioning dashboard data
- For battery issues: Provide specific troubleshooting advice first, only mention current battery percentage if directly relevant
- For maintenance issues: Provide specific advice first, mention service dates only if directly relevant
- For location questions: Provide specific information about nearby places
- For general questions: Provide helpful information without mentioning dashboard data
- Only suggest contacting SMV for issues that clearly require professional assistance
- Use "Namaste" only for the first message in a conversation (this is message {'1' if is_first_message else 'not the first'})
- Never use casual expressions like "Arre wah!" or other colloquial phrases

EXAMPLES OF GOOD RESPONSES:

For "hi":
"Hello! I'm your SMV E-rickshaw assistant. How can I help you today with your e-rickshaw?"

For "my e-rickshaw is not starting":
"This could be due to several reasons: 1) Check if the key is fully inserted and turned, 2) Ensure the battery connections are secure, 3) Verify the emergency cut-off switch is in the correct position. If these steps don't help, please contact SMV support at 1800-XXX-XXXX for technical assistance."

For "is there any school nearby?":
"Yes, the nearest school is APS Academy, about 1.1 km away. There's also City Montessori School at a distance of 2.3 km from your current location."

For "when was my last service":
"Your last service was on June 10th, 2024, and your next scheduled service is on December 10th, 2024. Regular maintenance helps ensure optimal performance of your e-rickshaw."

For "my battery is taking too much time to charge":
"This could be happening for several reasons: 1) The charger might be malfunctioning, 2) There could be loose connections, 3) The battery might be aging. Try using a different charger if available, and ensure all connections are secure. If the problem persists, it would be best to have it checked by a technician."

USER QUESTION: {message}"""
            
            # Generate response with the model
            logger.info("Sending prompt to Gemini API")
            response = model.generate_content(prompt)
            
            # Extract and validate the response text
            if hasattr(response, 'text') and response.text:
                response_text = response.text
                logger.info(f"Received valid response from Gemini: {response_text[:100]}...")
                
                # Store the conversation for future reference
                if session_id not in conversation_history:
                    conversation_history[session_id] = []
                conversation_history[session_id].append({"role": "user", "content": message})
                conversation_history[session_id].append({"role": "assistant", "content": response_text})
            else:
                logger.error("Invalid or empty response from Gemini API")
                response_text = "I apologize, but I'm experiencing technical difficulties. Please try again later."
            
            # Generate TTS audio (in try block to prevent errors)
            audio_url = None
            try:
                audio_url = google_tts(response_text, lang=language, speed=speed)
                logger.info(f"Generated audio URL: {audio_url}")
            except Exception as audio_error:
                logger.error(f"Error generating audio: {audio_error}")
            
            # Return successful response with all expected fields
            return jsonify({
                'response': response_text,
                'audio_url': audio_url,
                'session_id': session_id
            })
            
        except Exception as api_error:
            logger.error(f"API error: {str(api_error)}", exc_info=True)
            # Return a structured error response that the frontend can handle
            return jsonify({
                'error': str(api_error),
                'response': "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                'session_id': session_id
            })
            
    except Exception as e:
        logger.error(f"Unhandled error in chat endpoint: {str(e)}", exc_info=True)
        # Return error response with all expected fields
        return jsonify({
            'error': str(e),
            'response': "I apologize, but I'm experiencing technical difficulties. Please try again later.",
            'session_id': session_id
        })

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for speech-to-text."""
    logger.info("Transcribe endpoint called")
    
    # Check if ffmpeg is available
    if not check_ffmpeg_available():
        logger.error("FFmpeg is not available")
        return jsonify({'error': 'FFmpeg is not available on this server. Audio conversion cannot be performed.'}), 503
    
    if 'audio' not in request.files:
        logger.error("No audio file provided in request")
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    logger.info(f"Received audio file: {audio_file.filename}, Content-Type: {audio_file.content_type}, Size: {request.content_length} bytes")
    
    if request.content_length == 0 or audio_file.filename == '':
        logger.error("Empty audio file received")
        return jsonify({'error': 'Empty audio file received'}), 400
    
    # Save the audio file temporarily
    temp_webm = tempfile.NamedTemporaryFile(suffix='.webm', delete=False).name
    audio_file.save(temp_webm)
    logger.info(f"Saved temporary WebM file: {temp_webm}")
    
    # Check if the file was saved and has content
    if os.path.getsize(temp_webm) == 0:
        logger.error("Saved audio file is empty")
        return jsonify({'error': 'Received audio file is empty'}), 400
    
    try:
        # Convert WebM to WAV
        logger.info("Converting WebM to WAV")
        wav_file = convert_webm_to_wav(temp_webm)
        
        if not wav_file:
            logger.error("Failed to convert audio format")
            return jsonify({'error': 'Failed to convert audio format'}), 500
        
        logger.info(f"WAV file created: {wav_file}, size: {os.path.getsize(wav_file)} bytes")
        
        # Use direct Google API for transcription if speech_recognition is not available
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.info("Using direct transcription method since speech_recognition is not available")
            text = direct_transcribe_audio(wav_file)
        else:
            # Use speech_recognition if available
            logger.info("Using speech_recognition for transcription")
            text = transcribe_audio_with_google_api(wav_file)
        
        # Clean up temporary files
        try:
            os.remove(temp_webm)
            os.remove(wav_file)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")
        
        if text:
            logger.info(f"Transcription successful: '{text}'")
            return jsonify({'text': text})
        else:
            logger.warning("No transcription result")
            return jsonify({'error': 'Could not transcribe audio'}), 500
    except Exception as e:
        logger.error(f"Error in transcription endpoint: {e}", exc_info=True)
        return jsonify({'error': f'Error processing audio: {str(e)}'}), 500

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """API endpoint for text-to-speech."""
    data = request.json
    text = data.get('text', '')
    lang = data.get('language', 'en')
    speed = float(data.get('speed', 1.0))
    slow = speed < 1.0
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Generate audio
    audio_file = google_tts(text, lang=lang, slow=slow, speed=speed)
    
    if audio_file:
        return jsonify({'audio_url': audio_file})
    else:
        return jsonify({'error': 'Failed to generate audio'}), 500

# ----- Main Function -----
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs(os.path.join(app.static_folder, 'audio', 'cache'), exist_ok=True)
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 9090))
    
    # Run the application
    app.run(host="0.0.0.0", port=port, debug=True)
