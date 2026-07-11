// Auto-dismiss flash messages after 5 seconds
function initFlashes() {
    const flashMessages = document.querySelectorAll('.flash:not(.initialized)');
    
    flashMessages.forEach(function(flash) {
        flash.classList.add('initialized');
        
        // Auto-dismiss
        const timeoutId = setTimeout(function() {
            dismissFlash(flash);
        }, 5000);
        
        // Close button
        const closeBtn = flash.querySelector('.flash-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                clearTimeout(timeoutId);
                dismissFlash(flash);
            });
        }
    });
}

function dismissFlash(flash) {
    flash.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(function() {
        flash.remove();
    }, 300);
}

document.addEventListener('DOMContentLoaded', initFlashes);
document.addEventListener('turbo:load', initFlashes);


// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Form validation helper
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = 'var(--accent-danger)';
            isValid = false;
        } else {
            input.style.borderColor = '';
        }
    });
    
    return isValid;
}

// Smooth scroll to element
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Copy to clipboard helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show success message
        const flash = document.createElement('div');
        flash.className = 'flash flash-success';
        flash.innerHTML = `
            <span class="flash-icon">✓</span>
            <span class="flash-text">Copied to clipboard!</span>
        `;
        
        const container = document.querySelector('.flash-messages') || createFlashContainer();
        container.appendChild(flash);
        
        setTimeout(() => {
            flash.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => flash.remove(), 300);
        }, 2000);
    });
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    document.body.appendChild(container);
    return container;
}
