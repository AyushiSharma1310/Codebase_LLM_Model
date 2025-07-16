document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');
    const modelSelect = document.getElementById('model-select');
    const taskSelect = document.getElementById('task-select');
    const fileUpload = document.getElementById('file-upload');
    const uploadBtn = document.getElementById('upload-btn');
    const historyList = document.getElementById('history-list');
    const fileList = document.getElementById('file-list');

    marked.setOptions({ breaks: true, gfm: true, sanitize: false });

    let conversationId = sessionStorage.getItem('conversationId') || null;

    loadSavedMessages();
    loadChatHistory();

    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);

    uploadBtn?.addEventListener('click', () => {
        console.log('Upload button clicked');
        fileUpload?.click();
    });

    const sidebar = document.querySelector('.sidebar');
    uploadBtn?.insertAdjacentElement('afterend', fileList);

    async function loadUploadedFiles() {
        try {
            const res = await fetch('http://localhost:8000/list-files/');
            const data = await res.json();
            fileList.innerHTML = '';
            if (data.files && data.files.length > 0) {
                data.files.forEach(f => {
                    const li = document.createElement('li');
                    li.textContent = f;
                    li.style.cursor = 'pointer';
                    li.title = 'Click to ask a question about this file';
                    li.addEventListener('click', async () => {
                        const question = prompt(`Ask a question about ${f}:`);
                        if (!question) return;
                        const userMsgId = addMessage(`(File: ${f})\n${question}`, 'user');
                        saveMessage(userMsgId, `(File: ${f})\n${question}`, 'user');
                        typingIndicator.classList.add('active');
                        try {
                            const response = await fetch('http://localhost:8000/rag-query/', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ question: `File: ${f}\n${question}` })
                            });
                            const data = await response.json();
                            const botMsgId = addMessage(data.answer, 'bot');
                            saveMessage(botMsgId, data.answer, 'bot');
                        } catch {
                            const errorMsgId = addMessage('Sorry, there was an error processing your file question.', 'bot');
                            saveMessage(errorMsgId, 'Sorry, there was an error processing your file question.', 'bot');
                        } finally {
                            typingIndicator.classList.remove('active');
                        }
                    });
                    fileList.appendChild(li);
                });
            } else fileList.innerHTML = '<li>No files uploaded</li>';
        } catch {
            fileList.innerHTML = '<li>Could not load files</li>';
        }
    }

    async function loadChatHistoryAPI() {
        if (!historyList) return;
        try {
            const res = await fetch('http://localhost:8000/list-conversations/');
            const data = await res.json();
            historyList.innerHTML = '';
            if (data.conversations && data.conversations.length > 0) {
                data.conversations.forEach(cid => {
                    const li = document.createElement('li');
                    li.textContent = cid;
                    li.style.cursor = 'pointer';
                    li.addEventListener('click', () => {
                        sessionStorage.setItem('conversationId', cid);
                        location.reload();
                    });
                    historyList.appendChild(li);
                });
            } else historyList.innerHTML = '<li>No conversations</li>';
        } catch {
            historyList.innerHTML = '<li>Could not load history</li>';
        }
    }

    loadUploadedFiles();
    loadChatHistoryAPI();

    // Store uploaded files in memory
    let uploadedFiles = [];

    fileUpload?.addEventListener('change', async function () {
        const files = Array.from(this.files);
        const results = [];
        const model = modelSelect?.value || 'groq';
        const task = taskSelect?.value || 'summarize';
        fileList.innerHTML = '';
        for (const file of files) {
            const formData = new FormData();
            formData.append('model', model);
            formData.append('task', task);
            formData.append('file', file);
            try {
                const res = await fetch('http://localhost:8000/run_task', {
                    method: 'POST',
                    body: formData,
                });
                if (!res.ok) throw new Error('Network response was not ok');
                const json = await res.json();
                results.push(`✅ ${file.name} uploaded. Output: ${json.output || JSON.stringify(json)}`);
            } catch (err) {
                results.push(`❌ ${file.name} failed: ${err.message}`);
                console.error('Upload error:', err);
            }
            // Add file to UI with click-to-ask
            const li = document.createElement('li');
            li.textContent = file.name;
            li.style.cursor = 'pointer';
            li.title = 'Click to ask a question about this file';
            li.addEventListener('click', async () => {
                const question = prompt(`Ask a question about ${file.name}:`);
                if (!question) return;
                const userMsgId = addMessage(`(File: ${file.name})\n${question}`, 'user');
                saveMessage(userMsgId, `(File: ${file.name})\n${question}`, 'user');
                typingIndicator.classList.add('active');
                const askForm = new FormData();
                askForm.append('model', model);
                askForm.append('task', task);
                askForm.append('file', file);
                try {
                    const res = await fetch('http://localhost:8000/run_task', {
                        method: 'POST',
                        body: askForm,
                    });
                    if (!res.ok) throw new Error('Network response was not ok');
                    const json = await res.json();
                    const botMsgId = addMessage(json.output || JSON.stringify(json), 'bot');
                    saveMessage(botMsgId, json.output || JSON.stringify(json), 'bot');
                } catch (err) {
                    const errorMsgId = addMessage('Sorry, there was an error processing your file question.', 'bot');
                    saveMessage(errorMsgId, 'Sorry, there was an error processing your file question.', 'bot');
                    console.error('File question error:', err);
                } finally {
                    typingIndicator.classList.remove('active');
                }
            });
            fileList.appendChild(li);
        }
        alert(results.join('\n'));
    });

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        messageInput.disabled = true;
        sendButton.disabled = true;

        const userMsgId = addMessage(message, 'user');
        saveMessage(userMsgId, message, 'user');

        messageInput.value = '';
        messageInput.style.height = 'auto';

        typingIndicator.classList.add('active');

        try {
            const API_URL = window.location.hostname === 'localhost'
                ? 'http://localhost:8000'
                : 'https://coding-copilot.onrender.com';

            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `Task: ${taskSelect?.value || 'general'}\nModel: ${modelSelect?.value || 'groq'}\n\n${message}`,
                    conversation_id: conversationId
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();

            if (!conversationId) {
                conversationId = data.conversation_id;
                sessionStorage.setItem('conversationId', conversationId);
            }

            const botMsgId = addMessage(data.response, 'bot');
            saveMessage(botMsgId, data.response, 'bot');
            updateChatHistory();
        } catch (error) {
            const errorMsgId = addMessage('Sorry, there was an error processing your request. Please try again.', 'bot');
            saveMessage(errorMsgId, 'Sorry, there was an error processing your request. Please try again.', 'bot');
        } finally {
            typingIndicator.classList.remove('active');
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
        }
    }

    function addMessage(content, sender) {
        const messageId = 'msg-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.id = messageId;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = sender === 'bot' ? marked.parse(content) : content.replace(/\n/g, '<br>');

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(timeDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageId;
    }

    function saveMessage(id, content, sender) {
        const messages = JSON.parse(sessionStorage.getItem('chatMessages') || '[]');
        messages.push({ id, content, sender, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
        sessionStorage.setItem('chatMessages', JSON.stringify(messages));
    }

    function loadSavedMessages() {
        const messages = JSON.parse(sessionStorage.getItem('chatMessages') || '[]');
        if (messages.length > 0) {
            chatMessages.innerHTML = '';
            messages.forEach(msg => addMessage(msg.content, msg.sender));
        } else {
            addMessage('Hello! I\'m your Coding Copilot. How can I help you today?', 'bot');
        }
    }

    function updateChatHistory() {
        const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        if (!history.includes(conversationId)) {
            history.push(conversationId);
            localStorage.setItem('chatHistory', JSON.stringify(history));
        }
        loadChatHistory();
    }

    function loadChatHistory() {
        if (!historyList) return;
        const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        historyList.innerHTML = '';
        history.forEach(cid => {
            const li = document.createElement('li');
            li.textContent = cid;
            li.style.cursor = 'pointer';
            li.addEventListener('click', () => {
                sessionStorage.setItem('conversationId', cid);
                location.reload();
            });
            historyList.appendChild(li);
        });
    }

    const chatHeader = document.querySelector('.chat-header');
    const headerContainer = document.createElement('div');
    headerContainer.style.display = 'flex';
    headerContainer.style.justifyContent = 'space-between';
    headerContainer.style.alignItems = 'center';

    const title = chatHeader.querySelector('h1');
    chatHeader.removeChild(title);
    headerContainer.appendChild(title);

    const clearButton = document.createElement('button');
    clearButton.innerHTML = 'Clear Chat';
    clearButton.style.padding = '5px 10px';
    clearButton.style.background = '#2d2d2d';
    clearButton.style.color = '#ffffff';
    clearButton.style.border = '1px solid #404040';
    clearButton.style.borderRadius = '5px';
    clearButton.style.cursor = 'pointer';

    clearButton.addEventListener('click', () => {
        sessionStorage.removeItem('chatMessages');
        sessionStorage.removeItem('conversationId');
        localStorage.removeItem('chatHistory');
        location.reload();
    });

    headerContainer.appendChild(clearButton);
    chatHeader.appendChild(headerContainer);
});
