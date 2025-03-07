// NEW IMPLEMENTATION - Direct API Call Verifier
document.addEventListener('DOMContentLoaded', function() {
  console.log("NEW CHAT IMPLEMENTATION LOADING");
  
  // Find chat elements
  const chatForm = document.querySelector('form') || document.getElementById('chat-form');
  const messageInput = document.querySelector('input[type="text"]') || document.getElementById('message-input');
  const chatContainer = document.querySelector('.chat-messages, #chat-messages');
  
  if (!chatForm || !messageInput || !chatContainer) {
    console.error("Critical elements not found!", { form: chatForm, input: messageInput, container: chatContainer });
    // Try to recreate if missing
    createChatInterface();
    return;
  }
  
  // Destroy all existing event listeners
  const newForm = chatForm.cloneNode(true);
  if (chatForm.parentNode) {
    chatForm.parentNode.replaceChild(newForm, chatForm);
    console.log("Replaced chat form to remove all event listeners");
  }
  
  // Get references to the new elements
  const newChatForm = document.querySelector('form') || document.getElementById('chat-form');
  const newMessageInput = document.querySelector('input[type="text"]') || document.getElementById('message-input');
  
  if (!newChatForm || !newMessageInput) {
    console.error("Failed to get new form elements");
    return;
  }
  
  // Add debug element to page
  const debugDiv = document.createElement('div');
  debugDiv.id = 'chat-debug';
  debugDiv.style.position = 'fixed';
  debugDiv.style.bottom = '10px';
  debugDiv.style.right = '10px';
  debugDiv.style.backgroundColor = 'rgba(0,0,0,0.7)';
  debugDiv.style.color = 'white';
  debugDiv.style.padding = '5px';
  debugDiv.style.borderRadius = '5px';
  debugDiv.style.fontSize = '10px';
  debugDiv.style.maxWidth = '300px';
  debugDiv.style.zIndex = '9999';
  debugDiv.textContent = 'Chat Debug: Initialized';
  document.body.appendChild(debugDiv);
  
  // Function to update debug info
  function updateDebug(text) {
    const debugDiv = document.getElementById('chat-debug');
    if (debugDiv) {
      debugDiv.textContent = 'Chat Debug: ' + text;
      console.log("DEBUG: " + text);
    }
  }
  
  // Session ID for tracking
  const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
  updateDebug('Session created: ' + sessionId);
  
  // Add event listener for form submission
  newChatForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const message = newMessageInput.value.trim();
    
    if (message) {
      updateDebug('Sending: ' + message);
      
      // Display user message
      const userDiv = document.createElement('div');
      userDiv.className = 'user-message';
      userDiv.textContent = message;
      chatContainer.appendChild(userDiv);
      
      // Clear input
      newMessageInput.value = '';
      
      // Show loading indicator
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'loading-indicator';
      loadingDiv.innerHTML = '<span></span><span></span><span></span>';
      chatContainer.appendChild(loadingDiv);
      
      // Scroll to bottom
      chatContainer.scrollTop = chatContainer.scrollHeight;
      
      // DIRECT API CALL - Force using fetch to call our backend
      updateDebug('Calling API...');
      fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug': 'true' // Add debug header to track in logs
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId,
          timestamp: Date.now() // Add timestamp to prevent caching
        })
      })
      .then(response => {
        updateDebug('API responded: ' + response.status);
        if (!response.ok) {
          throw new Error('API error: ' + response.status);
        }
        return response.json();
      })
      .then(data => {
        // Remove loading indicator
        const loadingIndicator = document.querySelector('.loading-indicator');
        if (loadingIndicator) loadingIndicator.remove();
        
        updateDebug('Got data: ' + (data.response ? data.response.substring(0, 20) + '...' : 'No response'));
        
        if (data.response) {
          // Display bot message
          const botDiv = document.createElement('div');
          botDiv.className = 'bot-message';
          botDiv.innerHTML = data.response.replace(/\n/g, '<br>');
          chatContainer.appendChild(botDiv);
          
          // Scroll to bottom
          chatContainer.scrollTop = chatContainer.scrollHeight;
          
          // Play audio if available
          if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play().catch(e => console.error('Audio error:', e));
          }
        }
      })
      .catch(error => {
        updateDebug('Error: ' + error.message);
        
        // Remove loading indicator
        const loadingIndicator = document.querySelector('.loading-indicator');
        if (loadingIndicator) loadingIndicator.remove();
        
        // Display error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = 'Sorry, I encountered an error. Please try again.';
        chatContainer.appendChild(errorDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
      });
    }
  });
  
  // Function to create chat interface if missing
  function createChatInterface() {
    console.log("Attempting to create chat interface");
    // Implementation would go here if needed
  }
  
  updateDebug('Setup complete');
}); 