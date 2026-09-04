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
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
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

// --- GLOBAL AUDIT VALIDATION INTERCEPTOR ---
function initAuditInterceptor() {
    window._globalAuditSubmitHandler = function(e) {
        const form = e.target;
        // Verify it actually requires audit just in case
        if (!form.classList.contains('requires-audit') && !form.classList.contains('requires-high-risk-audit')) {
            return; // let it submit normally
        }
        
        e.preventDefault();
        
        const isHighRisk = form.classList.contains('requires-high-risk-audit');
        
        // Show modal
        const modal = document.getElementById('globalAuditModal');
        if (!modal) {
            console.error("Global audit modal not found in DOM");
            form.submit(); // fallback
            return;
        }
        
        modal.style.display = 'flex';
        
        // Ensure loader is hidden so it doesn't block the UI behind the modal
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.classList.remove('active');
            loader.style.display = 'none';
        }
        
        // Configure modal
        const formActionSpan = document.getElementById('auditModalActionName');
        if (formActionSpan && form.dataset.auditAction) {
            formActionSpan.textContent = form.dataset.auditAction;
        }
        
        const explanationContainer = document.getElementById('auditExplanationContainer');
        const explanationInput = document.getElementById('auditExplanationInput');
        const reasonSelect = document.getElementById('auditReasonSelect');
        
        reasonSelect.value = "";
        explanationInput.value = "";
        explanationInput.removeAttribute('required');
        explanationInput.minLength = 0;
        
        if (isHighRisk) {
            explanationContainer.style.display = 'block';
            explanationInput.setAttribute('required', 'required');
            explanationInput.minLength = 20;
            document.getElementById('auditExplanationHelp').textContent = "Minimum 20 characters required for high-risk actions.";
        } else {
            explanationContainer.style.display = 'none';
        }
        
        // Handle Reason Selection changes
        const onReasonChange = function() {
            if (reasonSelect.value === 'Other (Mandatory Explanation)') {
                explanationContainer.style.display = 'block';
                explanationInput.setAttribute('required', 'required');
                explanationInput.minLength = 10;
                document.getElementById('auditExplanationHelp').textContent = "Please provide details (minimum 10 characters).";
            } else if (!isHighRisk) {
                explanationContainer.style.display = 'none';
                explanationInput.removeAttribute('required');
                explanationInput.minLength = 0;
            }
        };
        reasonSelect.removeEventListener('change', window._auditReasonChangeHandler);
        window._auditReasonChangeHandler = onReasonChange;
        reasonSelect.addEventListener('change', onReasonChange);
        
        // Handle Submit
        const confirmBtn = document.getElementById('auditModalConfirmBtn');
        const onConfirm = function() {
            if (!reasonSelect.value) {
                alert("Please select a reason.");
                return;
            }
            
            if (explanationInput.hasAttribute('required') && explanationInput.value.length < explanationInput.minLength) {
                alert("Please provide a longer explanation (minimum " + explanationInput.minLength + " characters).");
                return;
            }
            
            // Add hidden inputs to form
            let reasonInput = form.querySelector('input[name="audit_reason"]');
            if (!reasonInput) {
                reasonInput = document.createElement('input');
                reasonInput.type = 'hidden';
                reasonInput.name = 'audit_reason';
                form.appendChild(reasonInput);
            }
            reasonInput.value = reasonSelect.value;
            
            let expInput = form.querySelector('input[name="audit_explanation"]');
            if (!expInput) {
                expInput = document.createElement('input');
                expInput.type = 'hidden';
                expInput.name = 'audit_explanation';
                form.appendChild(expInput);
            }
            expInput.value = explanationInput.value;
            
            modal.style.display = 'none';
            
            // Remove listeners to avoid memory leaks
            confirmBtn.removeEventListener('click', window._auditConfirmHandler);
            cancelBtn.removeEventListener('click', window._auditCancelHandler);
            
            // Actually submit the form
            form.submit();
        };
        
        if (window._auditConfirmHandler) {
            confirmBtn.removeEventListener('click', window._auditConfirmHandler);
        }
        window._auditConfirmHandler = onConfirm;
        confirmBtn.addEventListener('click', onConfirm);
        
        // Handle Cancel
        const cancelBtn = document.getElementById('auditModalCancelBtn');
        const onCancel = function() {
            modal.style.display = 'none';
            confirmBtn.removeEventListener('click', window._auditConfirmHandler);
            cancelBtn.removeEventListener('click', window._auditCancelHandler);
        };
        
        if (window._auditCancelHandler) {
            cancelBtn.removeEventListener('click', window._auditCancelHandler);
        }
        window._auditCancelHandler = onCancel;
        cancelBtn.addEventListener('click', onCancel);
    };

    const auditForms = document.querySelectorAll('.requires-audit, .requires-high-risk-audit');
    auditForms.forEach(form => {
        if (form.dataset.auditBound) return;
        form.dataset.auditBound = "true";
        form.addEventListener('submit', window._globalAuditSubmitHandler);
    });
}

document.addEventListener('turbo:load', initAuditInterceptor);
document.addEventListener("DOMContentLoaded", function() {
    initAuditInterceptor();
});
