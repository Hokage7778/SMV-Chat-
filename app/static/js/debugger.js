// Debugging tool to see where requests are going
console.log("Chat debugger loaded");

// Monitor all fetch requests
const originalFetch = window.fetch;
window.fetch = function() {
  console.log("Fetch called with URL:", arguments[0]);
  console.log("Fetch payload:", arguments[1]);
  return originalFetch.apply(this, arguments)
    .then(response => {
      console.log("Response status:", response.status);
      return response;
    })
    .catch(error => {
      console.error("Fetch error:", error);
      throw error;
    });
};

// Check if any global variables exist that might hold predefined responses
document.addEventListener('DOMContentLoaded', function() {
  console.log("Document loaded, scanning for chat components");
  
  // Log all script sources on the page
  document.querySelectorAll('script').forEach(script => {
    console.log("Found script:", script.src || "inline script");
  });
}); 