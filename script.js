let uploadedFiles = [];
let currentModel = 'llama3.1:8b';
let usePerplexity = false;

// Initialize the application
function initializeApp() {
    setupModelToggles();
    checkSystemStatus();
    console.log('EduGPT initialized');
}

// Setup model toggle functionality
function setupModelToggles() {
    const perplexityToggle = document.getElementById('usePerplexity');
    const localToggle = document.getElementById('useLocal');

    if (perplexityToggle && localToggle) {
        // Set initial state
        perplexityToggle.checked = usePerplexity;
        localToggle.checked = !usePerplexity;
        updateModelDisplay();

        // Add event listeners
        perplexityToggle.addEventListener('change', function() {
            if (this.checked) {
                usePerplexity = true;
                localToggle.checked = false;
            } else {
                usePerplexity = false;
                localToggle.checked = true;
            }
            updateModelDisplay();
        });

        localToggle.addEventListener('change', function() {
            if (this.checked) {
                usePerplexity = false;
                perplexityToggle.checked = false;
            } else {
                usePerplexity = true;
                perplexityToggle.checked = true;
            }
            updateModelDisplay();
        });
    }
}

// Update the model display
function updateModelDisplay() {
    const statusDot = document.getElementById('statusDot');
    const modelDisplay = document.getElementById('currentModelDisplay');

    if (usePerplexity) {
        statusDot.className = 'status-dot status-perplexity';
        modelDisplay.textContent = 'Perplexity AI (Online)';
        modelDisplay.style.color = '#007bff';
    } else {
        statusDot.className = 'status-dot status-local';
        modelDisplay.textContent = `Local Ollama (${currentModel})`;
        modelDisplay.style.color = '#28a745';
    }
}

// File upload handling (keep your existing file functions)
function handleFileSelect(files) {
    for (let file of files) {
        if (isFileSupported(file)) {
            uploadedFiles.push(file);
            displayUploadedFile(file);
        }
    }
}

function isFileSupported(file) {
    const supportedTypes = ['.pdf', '.docx', '.doc', '.txt', '.pptx'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    return supportedTypes.includes(fileExtension);
}

function displayUploadedFile(file) {
    const fileList = document.getElementById('fileList');
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <span class="file-name">${file.name}</span>
        <span class="file-remove" onclick="removeFile('${file.name}')">
            <i class="fas fa-times"></i>
        </span>
    `;
    fileList.appendChild(fileItem);
}

function removeFile(fileName) {
    uploadedFiles = uploadedFiles.filter(file => file.name !== fileName);
    document.getElementById('fileList').innerHTML = '';
    uploadedFiles.forEach(displayUploadedFile);
}

// Document processing
async function processDocuments() {
    if (uploadedFiles.length === 0) {
        alert('Please upload at least one file first!');
        return;
    }

    const formData = new FormData();
    uploadedFiles.forEach(file => {
        formData.append('files', file);
    });

    try {
        showLoading('Processing documents and building knowledge base...');
        
        const response = await fetch('/process-documents', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (result.success) {
            addMessage(`Successfully processed ${result.processed_files} documents! You can now ask questions about your study materials.`, 'bot');
            uploadedFiles = [];
            document.getElementById('fileList').innerHTML = '';
        } else {
            addMessage(`Error: ${result.error}`, 'bot');
        }
    } catch (error) {
        addMessage(`Error processing documents: ${error.message}`, 'bot');
    } finally {
        hideLoading();
    }
}

// Chat functionality
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();

    if (!message) return;

    addMessage(message, 'user');
    userInput.value = '';

    // Show which model is being used
    const modelType = usePerplexity ? 'Perplexity AI' : 'Local Ollama';
    showLoading(`Thinking with ${modelType}...`);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                use_perplexity: usePerplexity
            })
        });

        const data = await response.json();
        
        hideLoading();
        
        if (data.error) {
            addMessage(`Error: ${data.error}`, 'bot');
        } else if (data.response) {
            // Add model info to the response
            const modelInfo = usePerplexity ? 'Perplexity AI' : `Local Ollama (${currentModel})`;
            addMessage(data.response, 'bot', data.sources, modelInfo);
        } else {
            addMessage('Sorry, I encountered an unexpected error. Please try again.', 'bot');
        }
    } catch (error) {
        hideLoading();
        addMessage(`Network error: ${error.message}`, 'bot');
    }
}

function addMessage(message, sender, sources = null, modelInfo = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    let messageHTML = `<strong>${sender === 'user' ? 'You' : 'EduGPT'}:</strong> ${message}`;
    
    // Add model info for bot messages
    if (modelInfo && sender === 'bot') {
        messageHTML += `<div style="margin-top: 8px; font-size: 0.8rem; color: #666;">
            <i>Powered by: ${modelInfo}</i>
        </div>`;
    }
    
    if (sources && sources.length > 0) {
        messageHTML += `<div class="sources">
            <strong>Sources:</strong>`;
        sources.forEach(source => {
            messageHTML += `<div class="source-item">
                <strong>${source.filename}</strong> (Score: ${source.score?.toFixed(3) || 'N/A'})<br>
                ${source.content}
            </div>`;
        });
        messageHTML += '</div>';
    }
    
    messageDiv.innerHTML = messageHTML;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading(message) {
    const chatMessages = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loadingMessage';
    loadingDiv.className = 'message bot-message loading';
    loadingDiv.innerHTML = `<strong>EduGPT:</strong> ${message}`;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideLoading() {
    const loadingDiv = document.getElementById('loadingMessage');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Quick actions
function quickAction(action) {
    let prompt = '';
    
    switch(action) {
        case 'summarize':
            prompt = "Please provide a comprehensive summary of the main document.";
            break;
        case 'compare':
            prompt = "Compare two concepts from my materials.";
            break;
        case 'explain':
            prompt = "Explain the most complex topic in my documents.";
            break;
        case 'quiz':
            prompt = "Generate a quiz based on my study materials.";
            break;
    }
    
    document.getElementById('userInput').value = prompt;
    sendMessage();
}

// Check system status
async function checkSystemStatus() {
    try {
        const response = await fetch('/debug/status');
        const status = await response.json();
        console.log('System status:', status);
    } catch (error) {
        console.log('Could not check system status');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initializeApp);

// Drag and drop (keep your existing code)
const uploadArea = document.getElementById('uploadArea');
if (uploadArea) {
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#764ba2';
        uploadArea.style.backgroundColor = '#f8f9fa';
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = '#667eea';
        uploadArea.style.backgroundColor = 'transparent';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#667eea';
        uploadArea.style.backgroundColor = 'transparent';
        handleFileSelect(e.dataTransfer.files);
    });
}