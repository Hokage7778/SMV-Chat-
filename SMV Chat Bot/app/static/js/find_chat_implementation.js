// Add this debug script to identify the current chat implementation
console.log("Debugging chat implementation");
console.log("All scripts on page:", Array.from(document.querySelectorAll('script')).map(s => s.src || "inline"));
console.log("All event listeners:", getEventListeners(document));

// Try to find the chat form and any attached listeners
document.addEventListener('DOMContentLoaded', function() {
  const chatForm = document.querySelector('form, #chat-form');
  if (chatForm) {
    console.log("Found chat form:", chatForm);
    console.log("Form event listeners:", getEventListeners(chatForm));
  } else {
    console.log("No chat form found");
  }
}); 