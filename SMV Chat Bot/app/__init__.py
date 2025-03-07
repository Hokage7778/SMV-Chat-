from flask import Flask
from flask_cors import CORS
import os
import google.generativeai as genai

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Enable CORS
    CORS(app)
    
    # Configure static files to be cached for longer
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development
    
    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-for-development-only'),
        GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY'),
        TOMTOM_API_KEY=os.environ.get('TOMTOM_API_KEY')
    )
    
    # Initialize Google Generative AI
    try:
        genai.configure(api_key=app.config['GOOGLE_API_KEY'])
    except Exception as e:
        app.logger.error(f"Error configuring Google Generative AI: {e}")
    
    # Register routes
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Ensure the static folder exists
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'audio', 'cache'), exist_ok=True)
    
    return app 