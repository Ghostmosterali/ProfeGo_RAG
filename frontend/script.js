// ===== VARIABLES GLOBALES =====
let currentUser = null;
let currentToken = null;
const API_BASE = '/api';

// ===== ELEMENTOS DEL DOM =====
const loginSection = document.getElementById('login-section');
const mainSection = document.getElementById('main-section');
const authForm = document.getElementById('auth-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const authMessage = document.getElementById('auth-message');
const logoutBtn = document.getElementById('logout-btn');
const userInfo = document.getElementById('user-info');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');
const fileInput = document.getElementById('file-input');
const filesGallery = document.getElementById('files-gallery');

const navButtons = {
    inicio: document.getElementById('nav-inicio'),
    archivos: document.getElementById('nav-archivos'),
    acerca: document.getElementById('nav-acerca')
};

const contentSections = {
    inicio: document.getElementById('inicio-content'),
    archivos: document.getElementById('archivos-content'),
    acerca: document.getElementById('acerca-content')
};

const confirmModal = document.getElementById('confirm-modal');
const confirmMessage = document.getElementById('confirm-message');
const confirmYes = document.getElementById('confirm-yes');
const confirmNo = document.getElementById('confirm-no');

// ===== UTILIDADES =====
function showMessage(message, type = 'info') {
    authMessage.textContent = message;
    authMessage.className = `message ${type}`;
    authMessage.classList.remove('hidden');
    
    setTimeout(() => {
        authMessage.classList.add('hidden');
    }, 5000);
}

function showLoading(text = 'Cargando...') {
    loadingText.textContent = text;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showModal(message, onConfirm) {
    confirmMessage.textContent = message;
    confirmModal.classList.remove('hidden');
    
    confirmYes.onclick = () => {
        confirmModal.classList.add('hidden');
        onConfirm();
    };
    
    confirmNo.onclick = () => {
        confirmModal.classList.add('hidden');
    };
}

// ===== FUNCIONES DE API =====
async function apiRequest(endpoint, options = {}) {
    try {
        const headers = {};
        
        if (currentToken && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        } else if (!options.skipAuth) {
            throw new Error('Token no proporcionado');
        }
        
        if (options.body && typeof options.body === 'string') {
            headers['Content-Type'] = 'application/json';
        }
        
        Object.assign(headers, options.headers || {});
        
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la solicitud');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ===== AUTENTICACIÓN =====
async function login(email, password) {
    try {
        showLoading('Iniciando sesión...');
        
        const response = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        currentUser = response.email;
        currentToken = response.token;
        
        showMessage(response.message, 'success');
        
        // IMPORTANTE: Esperar 500ms antes de mostrar la app
        setTimeout(() => {
            showMainApp();
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
        
        showMessage(response.message, 'success');
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function logout() {
    currentUser = null;
    currentToken = null;
    
    loginSection.classList.remove('hidden');
    loginSection.classList.add('active');
    mainSection.classList.add('hidden');
    
    emailInput.value = '';
    passwordInput.value = '';
    authMessage.classList.add('hidden');
    
    switchToSection('inicio');
}

function showMainApp() {
    loginSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    
    userInfo.textContent = `Hola, ${currentUser}`;
    
    // Ir a la sección de inicio por defecto
    switchToSection('inicio');
}

// ===== NAVEGACIÓN =====
function switchToSection(sectionName) {
    Object.keys(navButtons).forEach(key => {
        navButtons[key].classList.toggle('active', key === sectionName);
    });
    
    Object.keys(contentSections).forEach(key => {
        contentSections[key].classList.toggle('active', key === sectionName);
        contentSections[key].classList.toggle('hidden', key !== sectionName);
    });
    
    // SOLO cargar archivos si vamos a esa sección Y tenemos token
    if (sectionName === 'archivos' && currentToken) {
        loadFiles();
    }
}

// ===== GESTIÓN DE ARCHIVOS =====
async function uploadFiles(files) {
    try {
        showLoading('Subiendo y procesando archivos...');
        
        if (!currentToken) {
            throw new Error('No hay sesión activa. Por favor inicia sesión.');
        }
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error subiendo archivos');
        }
        
        const result = await response.json();
        
        let message = `Archivos subidos: ${result.files_uploaded}`;
        if (result.files_processed > 0) {
            message += `\nArchivos procesados: ${result.files_processed}`;
        }
        
        showMessage(message, 'success');
        await loadFiles();
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadFiles() {
    try {
        if (!currentToken) {
            filesGallery.innerHTML = `
                <div class="empty-state">
                    <h3>Inicia sesión para ver tus archivos</h3>
                </div>
            `;
            return;
        }
        
        const files = await apiRequest('/files/list');
        displayFiles(files);
    } catch (error) {
        console.error('Error cargando archivos:', error);
        filesGallery.innerHTML = `
            <div class="empty-state">
                <h3>Error cargando archivos</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function displayFiles(files) {
    filesGallery.innerHTML = '';
    
    if (files.length === 0) {
        filesGallery.innerHTML = `
            <div class="empty-state">
                <h3>No hay archivos aún</h3>
                <p>Usa el botón 'Subir archivos' para agregar tus documentos</p>
            </div>
        `;
        return;
    }
    
    const originalFiles = files.filter(file => file.category === 'original');
    const processedFiles = files.filter(file => file.category === 'procesado');
    
    if (originalFiles.length > 0) {
        const originalSection = document.createElement('div');
        originalSection.innerHTML = `
            <div class="file-section-title">ARCHIVOS ORIGINALES (${originalFiles.length})</div>
        `;
        filesGallery.appendChild(originalSection);
        
        originalFiles.forEach(file => {
            filesGallery.appendChild(createFileCard(file));
        });
    }
    
    if (processedFiles.length > 0) {
        const processedSection = document.createElement('div');
        processedSection.innerHTML = `
            <div class="file-section-title procesados">ARCHIVOS PROCESADOS (.txt) (${processedFiles.length})</div>
        `;
        filesGallery.appendChild(processedSection);
        
        processedFiles.forEach(file => {
            filesGallery.appendChild(createFileCard(file));
        });
    }
}

function createFileCard(file) {
    const card = document.createElement('div');
    card.className = `file-card ${file.category}`;
    
    let icon = '📎';
    if (file.category === 'procesado') {
        icon = '📄';
    } else {
        const fileType = file.type.toLowerCase();
        if (fileType.includes('pdf')) icon = '📄';
        else if (fileType.includes('imagen')) icon = '🖼️';
        else if (fileType.includes('word')) icon = '📝';
        else if (fileType.includes('excel')) icon = '📊';
    }
    
    card.innerHTML = `
        <div class="file-info">
            <div class="file-name">
                <span class="file-icon">${icon}</span>
                <span>${file.name}</span>
            </div>
            <div class="file-details">
                <span>Tipo: ${file.type}</span>
                <span>Tamaño: ${file.size}</span>
            </div>
        </div>
        <div class="file-actions">
            <button class="delete-btn" onclick="confirmDeleteFile('${file.category}', '${file.name}')" title="Eliminar ${file.name}">
                🗑️
            </button>
        </div>
    `;
    
    return card;
}

async function deleteFile(category, filename) {
    try {
        showLoading('Eliminando archivo...');
        
        await apiRequest(`/files/delete/${category}/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        showMessage(`Archivo '${filename}' eliminado correctamente`, 'success');
        await loadFiles();
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function confirmDeleteFile(category, filename) {
    showModal(
        `¿Estás seguro de que quieres eliminar "${filename}"?`,
        () => deleteFile(category, filename)
    );
}

// ===== EVENT LISTENERS =====
document.addEventListener('DOMContentLoaded', function() {
    authForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            showMessage('Por favor completa todos los campos', 'error');
            return;
        }
        
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
        
        register(email, password);
    });
    
    logoutBtn.addEventListener('click', logout);
    
    Object.keys(navButtons).forEach(key => {
        navButtons[key].addEventListener('click', () => switchToSection(key));
    });
    
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
            e.target.value = '';
        }
    });
    
    confirmModal.addEventListener('click', function(e) {
        if (e.target === confirmModal) {
            confirmModal.classList.add('hidden');
        }
    });
});

window.confirmDeleteFile = confirmDeleteFile;

loginSection.classList.add('active');
mainSection.classList.add('hidden');