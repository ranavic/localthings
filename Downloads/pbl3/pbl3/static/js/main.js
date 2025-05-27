/*
 * SkillForge - Main JavaScript
 * Handles common interactive elements across the platform
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Course progress tracking
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        let targetWidth = bar.getAttribute('data-width');
        bar.style.width = targetWidth + '%';
    });
    
    // Add animation classes with delay
    animateElements();
    
    // Profile card hover effects
    initProfileCardEffects();
    
    // Enhanced form validation
    initFormValidation();

    // Notification handling
    const notificationBell = document.querySelector('.notification-bell');
    if (notificationBell) {
        notificationBell.addEventListener('click', function(e) {
            e.preventDefault();
            toggleNotifications();
        });
    }

    // Handle course search filtering
    const courseFilter = document.getElementById('course-filter');
    if (courseFilter) {
        courseFilter.addEventListener('change', function() {
            filterCourses();
        });
    }
    
    const searchInput = document.getElementById('course-search');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            filterCourses();
        });
    }
    
    // AI Tutor chat interface
    const chatForm = document.getElementById('ai-tutor-form');
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendTutorMessage();
        });
    }
    
    // Handle dashboard widgets
    initDashboardWidgets();
    
    // Gamification effects
    initGamificationEffects();
});

/**
 * Add animation classes with delays to create a cascade effect
 */
function animateElements() {
    const fadeElements = document.querySelectorAll('.animate-fade-in');
    fadeElements.forEach((element, index) => {
        // Add delay classes based on position in the DOM
        if (!element.classList.contains('delay-100') && 
            !element.classList.contains('delay-200') && 
            !element.classList.contains('delay-300') && 
            !element.classList.contains('delay-400') && 
            !element.classList.contains('delay-500')) {
            element.classList.add(`delay-${(index % 5 + 1) * 100}`);
        }
    });
    
    // Animate profile stats with counting effect
    const profileStatValues = document.querySelectorAll('.profile-stat-value');
    profileStatValues.forEach(stat => {
        const finalValue = parseInt(stat.textContent);
        if (!isNaN(finalValue)) {
            animateCount(stat, 0, finalValue, 1500);
        }
    });
}

/**
 * Animate counting up to a number
 */
function animateCount(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        element.textContent = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

/**
 * Initialize profile card hover effects
 * Note: 3D hover effects have been disabled to fix UI issues
 */
function initProfileCardEffects() {
    // Profile card hover effect has been disabled to prevent unwanted movement
    const profileCard = document.querySelector('.profile-card');
    if (profileCard) {
        // Remove any existing transform style
        profileCard.style.transform = 'none';
        
        // Clear any existing event listeners by cloning and replacing the element
        const newProfileCard = profileCard.cloneNode(true);
        profileCard.parentNode.replaceChild(newProfileCard, profileCard);
    }
}

/**
 * Initialize form validation with visual feedback
 */
function initFormValidation() {
    const forms = document.querySelectorAll('.auth-form form');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input:not([type="hidden"])');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                }
            });
        });
    });
}

/**
 * Initialize dashboard widgets
 */
function initDashboardWidgets() {
    const dashboardCards = document.querySelectorAll('.dashboard-card');
    dashboardCards.forEach(card => {
        // Add subtle hover animation
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 15px 30px rgba(0,0,0,0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.05)';
        });
    });
}

/**
 * Initialize gamification visual effects
 */
function initGamificationEffects() {
    // Add subtle pulse animation to badges and achievements
    const badges = document.querySelectorAll('.badge-level, .achievement-icon');
    badges.forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            this.classList.add('pulse-animation');
        });
        
        badge.addEventListener('mouseleave', function() {
            this.classList.remove('pulse-animation');
        });
    });
}

// Add pulse animation for badges
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    .pulse-animation {
        animation: pulse 0.8s ease-in-out;
    }
`;
document.head.appendChild(style);

// Function to toggle notification display
function toggleNotifications() {
    const notificationDropdown = document.querySelector('.notification-dropdown');
    if (notificationDropdown) {
        notificationDropdown.classList.toggle('show');
        
        if (notificationDropdown.classList.contains('show')) {
            fetchNotifications();
        }
    }
}

// Function to fetch user notifications
function fetchNotifications() {
    const notificationPanel = document.querySelector('.notification-panel .notification-list');
    
    // In a real implementation, this would be an AJAX call to the server
    // For now, we'll just show a loading indicator
    notificationPanel.innerHTML = '<div class="text-center p-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Simulate API call delay
    setTimeout(() => {
        // This would normally come from an API response
        notificationPanel.innerHTML = `
            <div class="notification-item unread">
                <div class="notification-content">
                    <strong>Course Completed</strong>
                    <p>Congratulations! You've completed "Introduction to JavaScript"</p>
                    <small class="text-muted">2 hours ago</small>
                </div>
            </div>
            <div class="notification-item">
                <div class="notification-content">
                    <strong>New Badge Earned</strong>
                    <p>You've earned the "Quick Learner" badge!</p>
                    <small class="text-muted">Yesterday</small>
                </div>
            </div>
            <div class="notification-item">
                <div class="notification-content">
                    <strong>Session Reminder</strong>
                    <p>Your mentorship session with David is tomorrow at 3 PM</p>
                    <small class="text-muted">2 days ago</small>
                </div>
            </div>
        `;
    }, 1000);
}

// Function to filter courses based on search and filters
function filterCourses() {
    const searchTerm = document.getElementById('course-search').value.toLowerCase();
    const filterValue = document.getElementById('course-filter').value;
    
    const courseCards = document.querySelectorAll('.course-card');
    
    courseCards.forEach(card => {
        const courseTitle = card.querySelector('.course-title').textContent.toLowerCase();
        const courseCategory = card.getAttribute('data-category');
        const courseDifficulty = card.getAttribute('data-difficulty');
        
        let showCard = courseTitle.includes(searchTerm);
        
        if (filterValue.startsWith('category-') && filterValue !== 'category-all') {
            const category = filterValue.replace('category-', '');
            showCard = showCard && (courseCategory === category);
        }
        
        if (filterValue.startsWith('difficulty-') && filterValue !== 'difficulty-all') {
            const difficulty = filterValue.replace('difficulty-', '');
            showCard = showCard && (courseDifficulty === difficulty);
        }
        
        card.style.display = showCard ? 'block' : 'none';
    });
}

// AI Tutor functionality
function sendTutorMessage() {
    const messageInput = document.getElementById('tutor-message');
    const message = messageInput.value.trim();
    
    if (message === '') return;
    
    const chatMessages = document.querySelector('.chat-messages');
    
    // Add user message
    const userMessageEl = document.createElement('div');
    userMessageEl.classList.add('message', 'message-sent');
    userMessageEl.textContent = message;
    chatMessages.appendChild(userMessageEl);
    
    // Clear input
    messageInput.value = '';
    
    // Add loading indicator for AI response
    const loadingEl = document.createElement('div');
    loadingEl.classList.add('message', 'message-received', 'loading');
    loadingEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    chatMessages.appendChild(loadingEl);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // In a real implementation, this would be an AJAX call to the AI service
    // Simulate AI response after a delay
    setTimeout(() => {
        // Remove loading indicator
        chatMessages.removeChild(loadingEl);
        
        // Add AI response
        const aiMessageEl = document.createElement('div');
        aiMessageEl.classList.add('message', 'message-received');
        aiMessageEl.textContent = getAIResponse(message);
        chatMessages.appendChild(aiMessageEl);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1500);
}

// Simple mock AI response function
function getAIResponse(message) {
    const responses = [
        "That's a great question! Let me explain this concept in more detail...",
        "Based on your learning history, I'd recommend focusing on these key points...",
        "You're making excellent progress! Here's what you should try next...",
        "I notice you might be struggling with this concept. Let's break it down step by step...",
        "Have you considered approaching the problem this way? It might help you understand better."
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
}

// Dashboard widget functions
function removeWidget(widgetId) {
    const widget = document.querySelector(`.dashboard-widget[data-widget-id="${widgetId}"]`);
    if (widget) {
        widget.remove();
        
        // In a real implementation, this would make an AJAX call to update user preferences
        console.log(`Widget ${widgetId} removed`);
    }
}

function configureWidget(widgetId) {
    // In a real implementation, this would open a configuration modal
    console.log(`Configuring widget ${widgetId}`);
    
    // Example implementation to show a configuration modal
    const modal = document.getElementById('widget-config-modal');
    if (modal) {
        // Set the widget ID in the modal
        const widgetIdInput = modal.querySelector('#config-widget-id');
        if (widgetIdInput) {
            widgetIdInput.value = widgetId;
        }
        
        // Show the modal
        new bootstrap.Modal(modal).show();
    }
}

function toggleWidgetMinimize(widgetId) {
    const widget = document.querySelector(`.dashboard-widget[data-widget-id="${widgetId}"]`);
    if (widget) {
        const widgetBody = widget.querySelector('.dashboard-widget-body');
        const minimizeIcon = widget.querySelector('.widget-control[data-action="minimize"] i');
        
        if (widgetBody) {
            widgetBody.classList.toggle('d-none');
            
            if (minimizeIcon) {
                if (widgetBody.classList.contains('d-none')) {
                    minimizeIcon.classList.remove('bi-dash');
                    minimizeIcon.classList.add('bi-plus');
                } else {
                    minimizeIcon.classList.remove('bi-plus');
                    minimizeIcon.classList.add('bi-dash');
                }
            }
            
            // In a real implementation, this would make an AJAX call to update user preferences
            console.log(`Widget ${widgetId} ${widgetBody.classList.contains('d-none') ? 'minimized' : 'expanded'}`);
        }
    }
}

// Certificate sharing function
function shareCertificate(certificateId) {
    // In a real implementation, this would open a sharing modal with social media options
    // For now, we'll just simulate copying a link to clipboard
    
    const shareUrl = `${window.location.origin}/certificates/public/${certificateId}/`;
    
    // Create a temporary input element
    const tempInput = document.createElement('input');
    tempInput.value = shareUrl;
    document.body.appendChild(tempInput);
    
    // Select and copy the link
    tempInput.select();
    document.execCommand('copy');
    
    // Remove the temporary element
    document.body.removeChild(tempInput);
    
    // Show a success message
    alert('Certificate link copied to clipboard!');
}
