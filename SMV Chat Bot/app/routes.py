from flask import Blueprint, render_template, request, jsonify, current_app
import logging
import datetime
from app.helpers.llm import get_llm_response
from app.helpers.tts import generate_tts

# Create blueprint
main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@main_bp.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for the chat."""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    language = data.get('language', 'en')
    speed = float(data.get('speed', 1.0))
    
    # Log the request
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{timestamp}] Chat request from {session_id}: {message}")
    
    try:
        # Get dashboard data (would come from database in production)
        dashboard = {
            "battery_percentage": "93",
            "vehicle_number": "UP32 BZ 5678",
            "last_service": "10 June 2024",
            "next_service": "10 December 2024",
            "driver_rating": "4.5",
            "location": "Lucknow, Uttar Pradesh"
        }
        
        # Get response from LLM
        response_text = get_llm_response(message, dashboard, session_id)
        
        # Generate TTS for the response
        audio_url = generate_tts(response_text, language, speed)
        
        # Return the response
        return jsonify({
            'response': response_text,
            'audio_url': audio_url,
            'session_id': session_id,
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        fallback_response = "Namaste! I am your SMV E-rickshaw assistant. I apologize, but I'm experiencing technical difficulties. Please try again. For assistance, contact SMV at 1800-XXX-XXXX"
        
        return jsonify({
            'error': str(e),
            'response': fallback_response
        }), 500 