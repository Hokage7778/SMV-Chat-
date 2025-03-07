// Simple chat implementation
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat.js loaded');
    
    // Select elements
    const chatButton = document.querySelector('.chat-button') || document.getElementById('open-chat');
    const chatWindow = document.querySelector('.chat-window') || document.getElementById('chat-window');
    const closeButton = document.getElementById('close-chat');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    
    // Generate session ID
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
    
    // Open/close chat
    if (chatButton) {
        chatButton.addEventListener('click', function() {
            chatWindow.classList.add('active');
        });
    }
    
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            chatWindow.classList.remove('active');
        });
    }
    
    // Handle form submission
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = messageInput.value.trim();
            if (!message) return;
            
            // Add user message
            const userDiv = document.createElement('div');
            userDiv.className = 'user-message';
            userDiv.textContent = message;
            chatMessages.appendChild(userDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            messageInput.value = '';
            
            // Show loading
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading-message';
            loadingDiv.textContent = 'Loading...';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Send message to backend
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading message
                loadingDiv.remove();
                
                // Add bot message
                if (data.response) {
                    const botDiv = document.createElement('div');
                    botDiv.className = 'bot-message';
                    botDiv.innerHTML = data.response.replace(/\n/g, '<br>');
                    chatMessages.appendChild(botDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Play audio if available
                    if (data.audio_url) {
                        const audio = new Audio(data.audio_url);
                        audio.play().catch(e => console.error('Audio error:', e));
                    }
                } else {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.textContent = 'Sorry, I could not process your request.';
                    chatMessages.appendChild(errorDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            })
            .catch(error => {
                // Remove loading message
                loadingDiv.remove();
                
                // Show error
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = 'Sorry, there was an error connecting to the server.';
                chatMessages.appendChild(errorDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        });
    }
}); 