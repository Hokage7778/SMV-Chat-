# SMV Green Super Application

A web application for e-rickshaw drivers with a dashboard showing driver information, current location, and a talking chatbot.

## Features

- Driver dashboard with vehicle information
- Real-time location tracking
- Traffic updates
- Nearby locations information
- AI-powered chatbot with voice interaction
- Text-to-speech capabilities

## Prerequisites

- Python 3.8 or higher
- Google API key for Generative AI
- FFmpeg (for audio processing)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/smv-green-super-app.git
   cd smv-green-super-app
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your Google API key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   USE_API_KEY_AUTH=true
   ```

5. Create the necessary directories:
   ```
   mkdir -p app/static/audio/cache
   mkdir -p app/static/css
   mkdir -p app/static/js
   mkdir -p app/templates
   ```

## Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:9090
   ```

## Getting a Google API Key

1. Go to the [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key and add it to your `.env` file

## Troubleshooting

- If you encounter authentication errors, make sure your Google API key is correctly set in the `.env` file.
- For audio-related issues, ensure FFmpeg is installed on your system and available in your PATH.
- If speech recognition is not working, check that the required dependencies are installed.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 