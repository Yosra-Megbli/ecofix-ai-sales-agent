// Client script for Ecofix Chat UI

document.addEventListener('DOMContentLoaded', () => {
    // Generate new Session ID on page load
    const sessionId = crypto.randomUUID();
    console.log(`[Ecofix UI] Generated Session ID: ${sessionId}`);

    // DOM Elements
    const chatForm = document.getElementById('chat-form-id');
    const userInput = document.getElementById('user-input-id');
    const chatMessages = document.getElementById('chat-messages-id');
    const typingIndicator = document.getElementById('typing-indicator-id');
    const sendBtn = document.getElementById('send-btn-id');

    // Base API URL (relative to serve static files correctly from same origin)
    const baseApiUrl = window.location.origin;

    // Helper to format hours/minutes
    function getFormattedTime() {
        const now = new Date();
        return now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    // Helper to scroll messages container to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Helper to append a message bubble
    function appendMessage(role, content) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Escape HTML to prevent XSS, but allow line breaks
        const safeText = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\n/g, '<br>');

        bubble.innerHTML = safeText;

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = getFormattedTime();
        bubble.appendChild(timeSpan);

        row.appendChild(bubble);
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    // Show/Hide typing indicator
    function setTyping(isTyping) {
        if (isTyping) {
            typingIndicator.classList.remove('hidden');
        } else {
            typingIndicator.classList.add('hidden');
        }
        scrollToBottom();
    }

    // Lock/Unlock form inputs
    function setFormLocked(isLocked) {
        userInput.disabled = isLocked;
        sendBtn.disabled = isLocked;
        if (!isLocked) {
            userInput.focus();
        }
    }

    // Start Chat Session
    async function startChat() {
        setTyping(true);
        setFormLocked(true);
        
        try {
            const url = `${baseApiUrl}/chat/start?session_id=${sessionId}`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to start chat session: ${response.statusText}`);
            }

            const data = await response.json();
            appendMessage('assistant', data.response);
        } catch (error) {
            console.error('Error starting chat session:', error);
            appendMessage('assistant', 'Désolé, impossible de démarrer la session de chat. Veuillez rafraîchir la page.');
        } finally {
            setTyping(false);
            setFormLocked(false);
        }
    }

    // Send message to the agent
    async function sendMessage(messageText) {
        setTyping(true);
        setFormLocked(true);

        try {
            const url = `${baseApiUrl}/chat`;
            const payload = {
                message: messageText,
                session_id: sessionId
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Failed to get response from agent: ${response.statusText}`);
            }

            const data = await response.json();
            appendMessage('assistant', data.response);
        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage('assistant', "Désolé, une erreur technique est survenue. Veuillez reformuler ou réessayer plus tard.");
        } finally {
            setTyping(false);
            setFormLocked(false);
        }
    }

    // Handle form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // Display user message in UI
        appendMessage('user', text);
        
        // Clear input field
        userInput.value = '';

        // Call agent API
        sendMessage(text);
    });

    // Initialize chat session on load
    startChat();
});
