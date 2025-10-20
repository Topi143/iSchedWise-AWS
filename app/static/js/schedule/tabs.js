// Tab Switching Functions

function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Deactivate all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById('content-' + tabName);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Activate selected tab button
    const selectedButton = document.getElementById('tab-' + tabName);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
    
    // Store active tab in localStorage
    localStorage.setItem('activeScheduleTab', tabName);
}

// Restore active tab on page load
document.addEventListener('DOMContentLoaded', function() {
    // Ensure all tabs are hidden first
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Then activate the correct tab
    const activeTab = localStorage.getItem('activeScheduleTab') || 'class';
    switchTab(activeTab);
});
