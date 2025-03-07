// Improved chat implementation with better error handling
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat.js loaded and running!');
    
    // Select elements
    const chatButton = document.getElementById('chat-button');
    const chatWindow = document.getElementById('chat-window');
    const closeChat = document.getElementById('close-chat');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    
    // Check if elements exist
    if (!chatButton || !chatWindow || !closeChat || !chatForm || !messageInput || !chatMessages) {
        console.error("Chat elements not found. Creating them dynamically.");
        createChatElements();
    }
    
    // Generate session ID
    const sessionId = generateSessionId();
    console.log("Chat initialized with session ID:", sessionId);
    
    // Toggle chat window
    chatButton.addEventListener('click', function() {
        chatWindow.classList.toggle('active');
        if (chatWindow.classList.contains('active')) {
            messageInput.focus();
        }
    });
    
    // Close chat window
    closeChat.addEventListener('click', function() {
        chatWindow.classList.remove('active');
    });
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (message === '') return;
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        messageInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message to backend
        sendMessage(message);
    });
    
    // Helper functions
    function appendUserMessage(message) {
        const div = document.createElement('div');
        div.className = 'user-message';
        div.textContent = message;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function appendBotMessage(message) {
        const div = document.createElement('div');
        div.className = 'bot-message';
        div.innerHTML = message.replace(/\n/g, '<br>');
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function appendErrorMessage(message) {
        const div = document.createElement('div');
        div.className = 'error-message';
        div.textContent = message;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function showLoading() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.className = 'loading-indicator';
        div.id = id;
        div.innerHTML = '<span></span><span></span><span></span>';
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }
    
    function hideLoading(id) {
        const element = document.getElementById(id);
        if (element) element.remove();
    }
    
    function playAudio(url) {
        const audio = new Audio(url);
        audio.play().catch(e => console.error('Audio error:', e));
    }
    
    // Create chat elements if not found
    function createChatElements() {
        console.log("Creating chat elements dynamically");
        
        // Create styles
        const style = document.createElement('style');
        style.textContent = `
            .chat-button {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background-color: #4CAF50;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 9998;
            }
            .chat-window {
                position: fixed;
                bottom: 90px;
                right: 20px;
                width: 350px;
                height: 500px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 5px 25px rgba(0,0,0,0.2);
                z-index: 9999;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                opacity: 0;
                transform: translateY(20px);
                transition: opacity 0.3s, transform 0.3s;
                pointer-events: none;
            }
            .chat-window.active {
                opacity: 1;
                transform: translateY(0);
                pointer-events: all;
            }
            .chat-header {
                background-color: #4CAF50;
                color: white;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .chat-messages {
                flex: 1;
                padding: 15px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
                background-color: #f5f5f5;
            }
            .user-message, .bot-message, .error-message {
                max-width: 80%;
                padding: 10px 15px;
                border-radius: 18px;
                word-wrap: break-word;
            }
            .user-message {
                align-self: flex-end;
                background-color: #4CAF50;
                color: white;
                border-bottom-right-radius: 5px;
            }
            .bot-message {
                align-self: flex-start;
                background-color: white;
                color: #333;
                border-bottom-left-radius: 5px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            .error-message {
                align-self: center;
                background-color: #ffebee;
                color: #c62828;
                font-size: 0.9rem;
            }
            .loading-indicator {
                align-self: flex-start;
                display: flex;
                gap: 5px;
            }
            .loading-indicator span {
                display: block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #4CAF50;
                animation: bounce 1.4s infinite ease-in-out both;
            }
            .loading-indicator span:nth-child(1) {
                animation-delay: -0.32s;
            }
            .loading-indicator span:nth-child(2) {
                animation-delay: -0.16s;
            }
            @keyframes bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
            #chat-form {
                display: flex;
                padding: 10px;
                background-color: white;
                border-top: 1px solid #f0f0f0;
            }
            #message-input {
                flex: 1;
                padding: 10px 15px;
                border: 1px solid #ddd;
                border-radius: 20px;
                outline: none;
                font-size: 14px;
            }
            #chat-form button {
                background-color: #4CAF50;
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-left: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #chat-form button:after {
                content: "➤";
                transform: rotate(90deg);
            }
        `;
        document.head.appendChild(style);
        
        // Create chat button
        const chatButton = document.createElement('div');
        chatButton.className = 'chat-button';
        chatButton.id = 'chat-button';
        chatButton.textContent = '💬';
        document.body.appendChild(chatButton);
        
        // Create chat window
        const chatWindow = document.createElement('div');
        chatWindow.className = 'chat-window';
        chatWindow.id = 'chat-window';
        chatWindow.innerHTML = `
            <div class="chat-header">
                <div>SMV AI Assistant</div>
                <button id="close-chat" style="background:none;border:none;color:white;font-size:20px;cursor:pointer;">×</button>
            </div>
            <div class="chat-messages" id="chat-messages"></div>
            <form id="chat-form">
                <input type="text" id="message-input" placeholder="Type your message...">
                <button type="submit"></button>
            </form>
        `;
        document.body.appendChild(chatWindow);
        
        // Re-select elements after creation
        closeChat = document.getElementById('close-chat');
        chatForm = document.getElementById('chat-form');
        messageInput = document.getElementById('message-input');
        chatMessages = document.getElementById('chat-messages');
    }
    
    // Generate a random session ID
    function generateSessionId() {
        return 'session_' + Math.random().toString(36).substring(2, 15);
    }
    
    // Add a message to the chat
    function addMessage(text, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        
        // Format links if present
        text = formatLinks(text);
        
        messageElement.innerHTML = text;
        
        // Add timestamp
        const timeElement = document.createElement('div');
        timeElement.classList.add('message-time');
        
        const now = new Date();
        timeElement.textContent = now.getHours() + ':' + 
            (now.getMinutes() < 10 ? '0' : '') + now.getMinutes();
        
        messageElement.appendChild(timeElement);
        
        chatMessages.appendChild(messageElement);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Format links in text
    function formatLinks(text) {
        // Simple URL regex
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, function(url) {
            return '<a href="' + url + '" target="_blank">' + url + '</a>';
        });
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        const typingElement = document.createElement('div');
        typingElement.classList.add('typing-indicator');
        typingElement.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('typing-dot');
            typingElement.appendChild(dot);
        }
        
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Hide typing indicator
    function hideTypingIndicator() {
        const typingElement = document.getElementById('typing-indicator');
        if (typingElement) {
            typingElement.remove();
        }
    }
    
    // Send message to backend
    function sendMessage(message) {
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                language: 'en',
                speed: 1.0
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add bot response to chat
            if (data.response) {
                addMessage(data.response, 'bot');
                
                // Play audio if available
                if (data.audio_url) {
                    playAudio(data.audio_url);
                }
            } else if (data.error) {
                addMessage('Sorry, I encountered an error: ' + data.error, 'bot');
            }
        })
        .catch(error => {
            hideTypingIndicator();
            addMessage('Sorry, there was a problem connecting to the server.', 'bot');
            console.error('Error:', error);
        });
    }
}); 