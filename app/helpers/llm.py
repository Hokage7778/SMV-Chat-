import google.generativeai as genai
import logging
import json

logger = logging.getLogger(__name__)

# Store conversation history
conversation_history = {}

def get_llm_response(message, dashboard, session_id):
    """Get a response from the LLM for the user's message."""
    try:
        # Create model
        model = genai.GenerativeModel(
            "gemini-pro",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )
        
        # Create or get chat session
        if session_id in conversation_history:
            # Use existing history
            chat = conversation_history[session_id]
        else:
            # Create new chat session
            chat = model.start_chat(history=[])
            conversation_history[session_id] = chat
            
            # Initialize with system prompt
            system_prompt = f"""You are the SMV E-rickshaw Assistant. You MUST follow these rules:

1. ALWAYS begin with "Namaste! I am your SMV E-rickshaw assistant."
2. ONLY answer questions about e-rickshaws, their maintenance, battery issues, or dashboard
3. For ANY non-e-rickshaw questions, respond ONLY with: "I can only assist with e-rickshaw related questions."
4. ALWAYS include relevant dashboard data in your responses
5. ALWAYS end with: "For assistance, contact SMV at 1800-XXX-XXXX"

Current dashboard data:
- Battery: {dashboard['battery_percentage']}%
- Vehicle: {dashboard['vehicle_number']}
- Last service: {dashboard['last_service']}
- Next service: {dashboard['next_service']}
- Driver rating: {dashboard['driver_rating']}
- Location: {dashboard['location']}"""
            
            # Send system prompt to initialize conversation
            chat.send_message(system_prompt)
        
        # Add dashboard context to the user message
        enhanced_message = f"""User Query: {message}

Remember to check the dashboard:
- Battery: {dashboard['battery_percentage']}%
- Vehicle: {dashboard['vehicle_number']}
- Last service: {dashboard['last_service']}
- Next service: {dashboard['next_service']}"""
        
        # Send message and get response
        logger.info(f"Sending message to Gemini: {enhanced_message[:100]}...")
        response = chat.send_message(enhanced_message)
        
        if not response.text:
            logger.error("Empty response from LLM")
            return "Namaste! I am your SMV E-rickshaw assistant. I apologize, but I'm experiencing technical difficulties. Please try again. For assistance, contact SMV at 1800-XXX-XXXX"
            
        logger.info(f"LLM response: {response.text[:100]}...")
        return response.text
        
    except Exception as e:
        logger.error(f"Error getting LLM response: {e}", exc_info=True)
 