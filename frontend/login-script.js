const authForm = document.getElementById('auth-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');

// Elementos de validación visual
const passwordRequirements = document.getElementById('password-requirements');
const reqLength = document.getElementById('req-length');
const reqUppercase = document.getElementById('req-uppercase');
const reqLowercase = document.getElementById('req-lowercase');
const reqNumber = document.getElementById('req-number');
const reqSpecial = document.getElementById('req-special');

// ===== VERIFICAR SI YA HAY SESIÓN ACTIVA =====
document.addEventListener('DOMContentLoaded', function() {
    // Si ya hay sesión activa, redirigir a menu
    if (loadSession()) {
        window.location.href = 'menu.html';
        return;
    }
    
    // Configurar event listeners
    setupEventListeners();
    setupPasswordValidation();
});

// ===== VALIDACIÓN VISUAL EN TIEMPO REAL =====
function setupPasswordValidation() {
    passwordInput.addEventListener('focus', function() {
        passwordRequirements.classList.remove('hidden');
    });
    
    passwordInput.addEventListener('blur', function() {
        // Ocultar si el campo está vacío
        if (!this.value) {
            passwordRequirements.classList.add('hidden');
        }
    });
    
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        
        // Validar longitud
        updateRequirement(reqLength, password.length >= 8);
        
        // Validar mayúscula
        updateRequirement(reqUppercase, /[A-Z]/.test(password));
        
        // Validar minúscula
        updateRequirement(reqLowercase, /[a-z]/.test(password));
        
        // Validar número
        updateRequirement(reqNumber, /[0-9]/.test(password));
        
        // Validar carácter especial
        updateRequirement(reqSpecial, /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password));
    });
}

function updateRequirement(element, isValid) {
    if (isValid) {
        element.classList.remove('invalid');
        element.classList.add('valid');
    } else {
        element.classList.remove('valid');
        element.classList.add('invalid');
    }
}

// ===== FUNCIÓN DE VALIDACIÓN DE CONTRASEÑA =====
function validatePassword(password) {
    const errors = [];
    
    if (password.length < 8) {
        errors.push('• Mínimo 8 caracteres');
    }
    
    if (!/[A-Z]/.test(password)) {
        errors.push('• Al menos una letra mayúscula');
    }
    
    if (!/[a-z]/.test(password)) {
        errors.push('• Al menos una letra minúscula');
    }
    
    if (!/[0-9]/.test(password)) {
        errors.push('• Al menos un número');
    }
    
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        errors.push('• Al menos un carácter especial (!@#$%&*...)');
    }
    
    if (errors.length > 0) {
        const errorMessage = 'La contraseña debe cumplir:\n' + errors.join('\n');
        showMessage(errorMessage, 'error');
        return false;
    }
    
    return true;
}

// ===== FUNCIONES DE AUTENTICACIÓN =====
async function login(email, password) {
    try {
        showLoading('Iniciando sesión...');
        
        const response = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        // Guardar sesión en localStorage
        saveSession(response.email, response.token);
        
        showMessage(response.message, 'success');
        
        // Redirigir a menu.html después de 500ms
        setTimeout(() => {
            window.location.href = 'menu.html';
        }, 500);
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function register(email, password) {
    try {
        showLoading('Registrando usuario...');
        
        const response = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        showMessage(response.message + ' - Ahora puedes iniciar sesión', 'success');
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    authForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            showMessage('Por favor completa todos los campos', 'error');
            return;
        }
        
        // Validación visual antes de enviar
        if (!validatePassword(password)) return;
        
        login(email, password);
    });
    
    registerBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            showMessage('Por favor completa todos los campos', 'error');
            return;
        }
        
        // Validación visual antes de enviar
        if (!validatePassword(password)) return;
        
        register(email, password);
    });
}

// ===== MODALES DE TÉRMINOS Y PRIVACIDAD =====
const overlay = document.getElementById('modal-overlay');
const termsModal = document.getElementById('terms-modal');
const privacyModal = document.getElementById('privacy-modal');

const openTermsBtn = document.getElementById('open-terms');
const openPrivacyBtn = document.getElementById('open-privacy');

const closeTermsBtn = document.getElementById('close-terms');
const closePrivacyBtn = document.getElementById('close-privacy');

// Función para abrir modal
function openModal(modal) {
    overlay.classList.add('active');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Función para cerrar modal
function closeModal(modal) {
    overlay.classList.remove('active');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// Event Listeners - Abrir modales
openTermsBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openModal(termsModal);
});

openPrivacyBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openModal(privacyModal);
});

// Event Listeners - Cerrar modales
closeTermsBtn.addEventListener('click', () => {
    closeModal(termsModal);
});

closePrivacyBtn.addEventListener('click', () => {
    closeModal(privacyModal);
});

// Cerrar al hacer clic en el overlay
overlay.addEventListener('click', () => {
    closeModal(termsModal);
    closeModal(privacyModal);
});

// Cerrar con la tecla ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal(termsModal);
        closeModal(privacyModal);
    }
});
