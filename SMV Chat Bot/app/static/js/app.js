// SMV Green Super Application - Minimal JavaScript
console.log("App.js loaded - minimal version");

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded in app.js - minimal version");
    
    // Update date and time
    updateDateTime();
    setInterval(updateDateTime, 60000);
    
    // Set up chat functionality
    initChatbot();
});

// Update date and time only
function updateDateTime() {
    const now = new Date();
    const dateEl = document.getElementById('current-date');
    const timeEl = document.getElementById('current-time');
    
    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric', 
            month: 'long', 
            day: 'numeric'
        });
    }
    
    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
}

// Initialize chatbot
function initChatbot() {
    const chatToggle = document.getElementById('chat-toggle');
    const closeChat = document.getElementById('close-chat');
    const chatbotPanel = document.getElementById('chatbot-panel');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const voiceBtn = document.getElementById('voice-input-btn');
    
    // Open chat panel
    if (chatToggle && chatbotPanel) {
        chatToggle.addEventListener('click', function() {
            chatbotPanel.classList.add('active');
        });
    }
    
    // Close chat panel
    if (closeChat && chatbotPanel) {
        closeChat.addEventListener('click', function() {
            chatbotPanel.classList.remove('active');
        });
    }
    
    // Send message
    if (sendBtn && chatInput) {
        sendBtn.addEventListener('click', function() {
            sendMessage();
        });
    }
    
    // Send on Enter key
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    // Voice recording simulation
    if (voiceBtn) {
        voiceBtn.addEventListener('click', function() {
            const recordingIndicator = document.getElementById('recording-indicator');
            if (recordingIndicator) {
                recordingIndicator.classList.add('active');
                
                // Simulate recording end after 1.5 seconds
                setTimeout(function() {
                    recordingIndicator.classList.remove('active');
                    chatInput.value = "Show me nearby schools";
                }, 1500);
            }
        });
    }
    
    // Function to send message
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Add user message
        addMessage(message, 'user');
        chatInput.value = '';
        
        // Simulate bot response
        setTimeout(function() {
            let botResponse = "I'm here to help with any questions about your vehicle or location.";
            
            // Simple response logic
            if (message.toLowerCase().includes('hello') || message.toLowerCase().includes('hi')) {
                botResponse = "Hello! How can I assist you today?";
            } else if (message.toLowerCase().includes('school')) {
                botResponse = "The nearest school is City Public School, about 1.2 km away.";
            } else if (message.toLowerCase().includes('bus')) {
                botResponse = "The nearest bus stand is Central Bus Terminal, about 0.4 km away.";
            } else if (message.toLowerCase().includes('mall') || message.toLowerCase().includes('shop')) {
                botResponse = "The nearest mall is City Center Mall, about 0.9 km away.";
            } else if (message.toLowerCase().includes('battery')) {
                botResponse = "Your battery is at 87%. Based on your driving patterns, you can travel approximately 65 km more.";
            } else if (message.toLowerCase().includes('service')) {
                botResponse = "Your next service is scheduled for 10 December 2023.";
            }
            
            // Add bot response
            addMessage(botResponse, 'bot');
        }, 800);
    }
    
    // Add message to chat
    function addMessage(text, sender) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}
