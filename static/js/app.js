/**
 * AI Chatbot Studio - Frontend Application Engine
 * Handles real-time SSE streaming, MongoDB state sync, Markdown parsing & UI interaction.
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        currentChatId: null,
        chats: [],
        messages: [],
        attachedFiles: [],
        isGenerating: false,
        activeModel: 'gemini-2.5-flash',
        systemPrompt: 'You are NEXORA AI, a professional, intelligent, helpful, and context-aware AI assistant. Provide accurate, detailed, and well-structured answers. For programming questions, always use the language explicitly requested. Reply in the same language as the user. Never invent facts.',
        currentUser: null,
        token: localStorage.getItem('ai_bot_token') || null
    };

    // DOM Elements
    const elements = {
        sidebar: document.getElementById('sidebar'),
        toggleSidebarBtn: document.getElementById('toggleSidebarBtn'),
        mobileMenuBtn: document.getElementById('mobileMenuBtn'),
        newChatBtn: document.getElementById('newChatBtn'),
        chatList: document.getElementById('chatList'),
        searchChatInput: document.getElementById('searchChatInput'),
        currentChatTitle: document.getElementById('currentChatTitle'),
        welcomeContainer: document.getElementById('welcomeContainer'),
        messagesFeed: document.getElementById('messagesFeed'),
        chatViewport: document.getElementById('chatViewport'),
        promptInput: document.getElementById('promptInput'),
        sendBtn: document.getElementById('sendBtn'),
        attachBtn: document.getElementById('attachBtn'),
        fileInput: document.getElementById('fileInput'),
        attachmentPreview: document.getElementById('attachmentPreview'),
        
        // Modals
        settingsBtn: document.getElementById('settingsBtn'),
        settingsModal: document.getElementById('settingsModal'),
        closeSettingsModal: document.getElementById('closeSettingsModal'),
        cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
        saveSettingsBtn: document.getElementById('saveSettingsBtn'),
        modalMongoUri: document.getElementById('modalMongoUri'),
        modalGeminiKey: document.getElementById('modalGeminiKey'),
        modalOpenAIKey: document.getElementById('modalOpenAIKey'),

        systemPromptBtn: document.getElementById('systemPromptBtn'),
        systemPromptModal: document.getElementById('systemPromptModal'),
        closeSystemModal: document.getElementById('closeSystemModal'),
        cancelSystemBtn: document.getElementById('cancelSystemBtn'),
        saveSystemBtn: document.getElementById('saveSystemBtn'),
        systemPromptInput: document.getElementById('systemPromptInput'),

        // User Account & Auth Modal
        userAccountCard: document.getElementById('userAccountCard'),
        userAvatar: document.getElementById('userAvatar'),
        userName: document.getElementById('userName'),
        userEmail: document.getElementById('userEmail'),
        authActionBtn: document.getElementById('authActionBtn'),
        authActionIcon: document.getElementById('authActionIcon'),

        authModal: document.getElementById('authModal'),
        authModalTitle: document.getElementById('authModalTitle'),
        closeAuthModal: document.getElementById('closeAuthModal'),
        tabLoginBtn: document.getElementById('tabLoginBtn'),
        tabRegisterBtn: document.getElementById('tabRegisterBtn'),
        loginForm: document.getElementById('loginForm'),
        registerForm: document.getElementById('registerForm'),
        loginEmailInput: document.getElementById('loginEmailInput'),
        loginPasswordInput: document.getElementById('loginPasswordInput'),
        regUsernameInput: document.getElementById('regUsernameInput'),
        regEmailInput: document.getElementById('regEmailInput'),
        regPasswordInput: document.getElementById('regPasswordInput'),
        authErrorMsg: document.getElementById('authErrorMsg'),
        loginSubmitBtn: document.getElementById('loginSubmitBtn'),
        regSubmitBtn: document.getElementById('regSubmitBtn')
    };

    // Configure Marked.js options
    if (window.marked) {
        marked.setOptions({
            gfm: true,
            breaks: true,
            highlight: function (code, lang) {
                if (window.hljs && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (e) {}
                }
                return code;
            }
        });
    }

    // --- Core API Helpers ---
    async function apiFetch(url, options = {}) {
        try {
            const headers = { 'Content-Type': 'application/json', ...options.headers };
            if (state.token) {
                headers['Authorization'] = `Bearer ${state.token}`;
            }
            const response = await fetch(url, {
                headers: headers,
                ...options
            });
            return await response.json();
        } catch (err) {
            console.error(`API Fetch Error [${url}]:`, err);
            return { status: 'error', detail: err.message };
        }
    }

    // --- Initialization & Health Check ---
    async function init() {
        setupEventListeners();
        await checkAuthSession();
        await checkHealth();
        await loadChats();
        
        // Auto-refresh health every 15 seconds
        setInterval(checkHealth, 15000);
    }

    async function checkHealth() {
        await apiFetch('/api/health');
    }

    // --- Chat List & History Management ---
    async function loadChats() {
        const res = await apiFetch('/api/chats');
        if (res.status === 'success') {
            state.chats = res.chats || [];
            renderChatList();
        }
    }

    function renderChatList(filterQuery = '') {
        elements.chatList.innerHTML = '';
        const filtered = state.chats.filter(c => 
            c.title.toLowerCase().includes(filterQuery.toLowerCase())
        );

        if (filtered.length === 0) {
            elements.chatList.innerHTML = `
                <div style="padding: 0.8rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
                    No conversations found
                </div>
            `;
            return;
        }

        filtered.forEach(chat => {
            const item = document.createElement('div');
            item.className = `chat-item ${chat.id === state.currentChatId ? 'active' : ''}`;
            item.dataset.id = chat.id;

            item.innerHTML = `
                <i class="fa-regular fa-message" style="margin-right: 0.6rem; font-size: 0.85rem;"></i>
                <div class="chat-item-title">${escapeHtml(chat.title)}</div>
                <button class="icon-btn chat-item-del" data-id="${chat.id}" title="Delete chat">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;

            item.addEventListener('click', (e) => {
                if (e.target.closest('.chat-item-del')) return;
                switchChat(chat.id);
            });

            const delBtn = item.querySelector('.chat-item-del');
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                e.preventDefault();
                await deleteChat(chat.id);
            });

            elements.chatList.appendChild(item);
        });
    }

    async function switchChat(chatId) {
        state.currentChatId = chatId;
        renderChatList(elements.searchChatInput.value);

        const res = await apiFetch(`/api/chats/${chatId}`);
        if (res.status === 'success') {
            elements.currentChatTitle.innerHTML = `<span>${escapeHtml(res.chat.title)}</span>`;
            state.systemPrompt = res.chat.system_prompt || state.systemPrompt;
            elements.systemPromptInput.value = state.systemPrompt;
            
            state.messages = res.messages || [];
            renderMessagesFeed();
        }
    }

    async function deleteChat(chatId) {
        state.chats = state.chats.filter(c => c.id !== chatId);
        if (state.currentChatId === chatId) {
            resetToWelcomeScreen();
        } else {
            renderChatList(elements.searchChatInput.value);
        }

        await apiFetch(`/api/chats/${chatId}`, { method: 'DELETE' });
        await loadChats();
    }

    function resetToWelcomeScreen() {
        state.currentChatId = null;
        state.messages = [];
        elements.currentChatTitle.innerHTML = `<span>New Conversation</span>`;
        elements.welcomeContainer.style.display = 'flex';
        elements.messagesFeed.style.display = 'none';
        elements.messagesFeed.innerHTML = '';
        renderChatList(elements.searchChatInput.value);
    }

    // --- Message Rendering & Formatting ---
    function renderMessagesFeed() {
        if (state.messages.length === 0) {
            elements.welcomeContainer.style.display = 'flex';
            elements.messagesFeed.style.display = 'none';
            return;
        }

        elements.welcomeContainer.style.display = 'none';
        elements.messagesFeed.style.display = 'flex';
        elements.messagesFeed.innerHTML = '';

        state.messages.forEach(msg => {
            appendMessageToUI(msg.role, msg.content, msg.id);
        });

        scrollToBottom();
    }

    function appendMessageToUI(role, content, msgId = null) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;
        if (msgId) row.dataset.id = msgId;

        const isUser = role === 'user';
        const avatarHtml = isUser 
            ? '<i class="fa-solid fa-user"></i>'
            : `<img src="/static/assets/nexora-ai-avatar.png?v=2.0" class="nexora-avatar-img" alt="NEXORA AI">`;

        const parsedContent = formatMarkdown(content);

        row.innerHTML = `
            <div class="avatar">${avatarHtml}</div>
            <div class="bubble">
                <div class="bubble-content">${parsedContent}</div>
            </div>
        `;

        elements.messagesFeed.appendChild(row);
        attachCodeCopyListeners(row);
        scrollToBottom();
        return row;
    }

    function formatMarkdown(text) {
        if (!window.marked) return escapeHtml(text);
        try {
            return marked.parse(text);
        } catch (e) {
            return escapeHtml(text);
        }
    }

    function attachCodeCopyListeners(container) {
        const codeBlocks = container.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            const pre = block.parentElement;
            if (pre.querySelector('.code-header')) return; // already attached

            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `
                <span><code>code</code></span>
                <button class="copy-code-btn"><i class="fa-regular fa-copy"></i> Copy Code</button>
            `;

            pre.insertBefore(header, block);

            const copyBtn = header.querySelector('.copy-code-btn');
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(block.innerText);
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy Code';
                }, 2000);
            });
        });
    }

    function scrollToBottom() {
        elements.chatViewport.scrollTop = elements.chatViewport.scrollHeight;
    }

    // --- File, PDF & Image Attachment Handler ---
    function handleFileSelection(e) {
        const files = Array.from(e.target.files);
        files.forEach(file => {
            const reader = new FileReader();
            const lowerName = file.name.toLowerCase();
            const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(lowerName);
            const isPdf = file.type === 'application/pdf' || lowerName.endsWith('.pdf');
            
            reader.onload = (event) => {
                state.attachedFiles.push({
                    name: file.name,
                    size: file.size,
                    type: file.type || (isImage ? 'image/png' : isPdf ? 'application/pdf' : 'text/plain'),
                    isImage: isImage,
                    isPdf: isPdf,
                    content: event.target.result
                });
                renderAttachmentPills();
            };

            if (isImage || isPdf) {
                reader.readAsDataURL(file);
            } else {
                reader.readAsText(file);
            }
        });
        if (elements.fileInput) elements.fileInput.value = '';
    }

    function renderAttachmentPills() {
        if (!elements.attachmentPreview) return;
        elements.attachmentPreview.innerHTML = '';
        state.attachedFiles.forEach((file, index) => {
            const pill = document.createElement('div');
            pill.className = 'attachment-pill';
            
            let iconHtml = `<i class="fa-regular fa-file-code"></i>`;
            if (file.isImage) {
                iconHtml = `<img src="${file.content}" style="width:20px;height:20px;border-radius:4px;object-fit:cover;">`;
            } else if (file.isPdf) {
                iconHtml = `<i class="fa-solid fa-file-pdf" style="color: #EF4444;"></i>`;
            }

            pill.innerHTML = `
                ${iconHtml}
                <span>${escapeHtml(file.name)}</span>
                <i class="fa-solid fa-xmark remove-pill" title="Remove attachment"></i>
            `;
            pill.querySelector('.remove-pill').addEventListener('click', () => {
                state.attachedFiles.splice(index, 1);
                renderAttachmentPills();
            });
            elements.attachmentPreview.appendChild(pill);
        });
    }

    // --- NEXORA AI Real-Time Capabilities Engine (Weather, Location, Time, Date) ---

    function renderWeatherCardHTML(data) {
        const icon = data.icon || '☀️';
        const location = data.location_full || data.city || 'Current Location';
        const temp = data.temperature !== undefined ? data.temperature : '--';
        const feels = data.feels_like !== undefined ? data.feels_like : '--';
        const condition = data.condition || 'Clear';
        const humidity = data.humidity !== undefined ? data.humidity : '--';
        const wind = data.wind_speed !== undefined ? data.wind_speed : '--';
        const dir = data.wind_direction || 'N';
        const updated = data.updated_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        return `
<div class="nexora-weather-card">
    <div class="weather-card-header">
        <div class="weather-location-title">
            <i class="fa-solid fa-location-dot"></i>
            <span>${escapeHtml(location)}</span>
        </div>
        <div class="weather-badge-icon">${icon}</div>
    </div>
    <div class="weather-main-section">
        <div class="weather-temp-display">${temp}°C</div>
        <div class="weather-condition-tag">${escapeHtml(condition)}</div>
    </div>
    <div class="weather-details-grid">
        <div class="weather-detail-item"><i class="fa-solid fa-temperature-half"></i> Feels like: <strong>${feels}°C</strong></div>
        <div class="weather-detail-item"><i class="fa-solid fa-droplet"></i> Humidity: <strong>${humidity}%</strong></div>
        <div class="weather-detail-item"><i class="fa-solid fa-wind"></i> Wind: <strong>${wind} km/h</strong></div>
        <div class="weather-detail-item"><i class="fa-solid fa-compass"></i> Direction: <strong>${dir}</strong></div>
    </div>
    <div class="weather-card-footer">
        <i class="fa-solid fa-clock"></i> Real-Time Weather • Updated at ${updated}
    </div>
</div>`;
    }

    function renderTimeCardHTML(data) {
        const loc = data.location || 'Local Time';
        const timeStr = data.time_formatted || data.time_short || new Date().toLocaleTimeString();
        const dateStr = data.date_formatted || new Date().toLocaleDateString();
        const tz = data.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;

        return `
<div class="nexora-time-card">
    <div class="time-card-header">
        <i class="fa-solid fa-clock"></i>
        <span>Current Time in ${escapeHtml(loc)}</span>
    </div>
    <div class="time-main-display">${timeStr}</div>
    <div class="time-date-subtext">${dateStr}</div>
    <div class="time-zone-badge">
        <i class="fa-solid fa-globe"></i> Timezone: ${tz}
    </div>
</div>`;
    }

    function generateCurrentTimeCard() {
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
        const now = new Date();
        const timeFormatted = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        const dateFormatted = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

        return renderTimeCardHTML({
            location: 'Local Time',
            time_formatted: timeFormatted,
            date_formatted: dateFormatted,
            timezone: userTz
        });
    }

    function generateCurrentDateCard() {
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata';
        const now = new Date();
        const dateFormatted = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

        return `
<div class="nexora-time-card">
    <div class="time-card-header">
        <i class="fa-solid fa-calendar-day"></i>
        <span>Today's Date</span>
    </div>
    <div class="time-main-display" style="font-size: 2.2rem;">${dateFormatted}</div>
    <div class="time-zone-badge" style="margin-top: 0.5rem;">
        <i class="fa-solid fa-globe"></i> System Timezone: ${userTz}
    </div>
</div>`;
    }

    async function fetchCurrentLocationWeather() {
        if (!navigator.geolocation) {
            return `Sure! Which city's weather would you like me to check? (e.g. Weather in Mumbai, Patna, or Delhi)`;
        }

        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    try {
                        const res = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
                        const data = await res.json();
                        if (data.status === 'success') {
                            resolve(renderWeatherCardHTML(data));
                        } else {
                            resolve(`Sure! Which city's weather would you like me to check?`);
                        }
                    } catch (err) {
                        resolve(`Failed to connect to weather service. Please check your network connection.`);
                    }
                },
                (error) => {
                    resolve(`Sure — what city's weather would you like me to check?`);
                },
                { timeout: 8000, enableHighAccuracy: true }
            );
        });
    }

    async function fetchCityWeather(city) {
        try {
            const res = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
            const data = await res.json();
            if (data.status === 'success') {
                return renderWeatherCardHTML(data);
            } else {
                return `I couldn't find real-time weather information for **"${escapeHtml(city)}"**. Please verify the city name and try again (e.g. *Weather in Mumbai*, *Weather in London*, *Weather in Patna*).`;
            }
        } catch (err) {
            return `Failed to connect to weather services. Please check your internet connection.`;
        }
    }

    async function fetchCityTimeCard(city) {
        try {
            const res = await fetch(`/api/time?city=${encodeURIComponent(city)}`);
            const data = await res.json();
            if (data.status === 'success') {
                return renderTimeCardHTML(data);
            }
        } catch (err) {}
        return generateCurrentTimeCard();
    }

    async function fetchUserLocationInfo() {
        if (!navigator.geolocation) {
            return `Location services are unsupported in your browser environment.`;
        }
        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                async (pos) => {
                    try {
                        const res = await fetch(`/api/weather?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`);
                        const data = await res.json();
                        if (data.status === 'success') {
                            resolve(`📍 **Your Current Detected Location**:\n\n### ${data.location_full}\n\n* **Coordinates**: ${pos.coords.latitude.toFixed(4)}° N, ${pos.coords.longitude.toFixed(4)}° E\n* **Timezone**: ${Intl.DateTimeFormat().resolvedOptions().timeZone}`);
                        } else {
                            resolve(`📍 **Your Coordinates**: ${pos.coords.latitude.toFixed(4)}° N, ${pos.coords.longitude.toFixed(4)}° E`);
                        }
                    } catch (e) {
                        resolve(`📍 **Your Coordinates**: ${pos.coords.latitude.toFixed(4)}° N, ${pos.coords.longitude.toFixed(4)}° E`);
                    }
                },
                (err) => {
                    resolve(`I need your location permission to detect your position. Please grant browser location access and try again.`);
                }
            );
        });
    }

    async function handleRealtimeIntent(rawText) {
        if (!rawText) return null;
        const prompt = rawText.trim().toLowerCase();

        // Pattern 1: City Weather (e.g. "weather in Mumbai", "temperature in Patna", "what is the weather in Delhi?", "weather for London")
        const cityWeatherMatch = prompt.match(/(?:weather|temperature|temp|climate)\s+(?:in|for|at|of)\s+([a-zA-Z\s]{2,30})/i) || prompt.match(/(?:how's|how is)\s+(?:the\s+)?weather\s+(?:in|at|for)\s+([a-zA-Z\s]{2,30})/i);
        if (cityWeatherMatch && cityWeatherMatch[1]) {
            const cityCandidate = cityWeatherMatch[1].replace(/[\?\!]/g, '').trim();
            if (cityCandidate && !['my current location', 'my location', 'here', 'near me', 'today'].includes(cityCandidate)) {
                return await fetchCityWeather(cityCandidate);
            }
        }

        // Pattern 2: Current Weather (e.g. "weather today in my current location", "weather near me", "temperature right now", "how is weather today", "weather here")
        if (/(weather|temperature|temp).*?(current|my location|near me|here|today|right now)/.test(prompt) || /how'?s?\s+(the\s+)?weather\s+today/.test(prompt) || prompt === 'weather' || prompt === 'current weather') {
            return await fetchCurrentLocationWeather();
        }

        // Pattern 3: City Time (e.g. "what time is it in London", "time in Tokyo", "what's the time in New York?")
        const cityTimeMatch = prompt.match(/(?:time|clock)\s+(?:is\s+it\s+)?(?:in|for|at|of)\s+([a-zA-Z\s]{2,30})/i) || prompt.match(/what.*?time.*?(?:in|for|at|of)\s+([a-zA-Z\s]{2,30})/i);
        if (cityTimeMatch && cityTimeMatch[1]) {
            const cityCandidate = cityTimeMatch[1].replace(/[\?\!]/g, '').trim();
            if (cityCandidate && !['my current location', 'my location', 'here', 'right now', 'now'].includes(cityCandidate)) {
                return await fetchCityTimeCard(cityCandidate);
            }
        }

        // Pattern 4: Current Time (e.g. "what time is it right now", "what is the current time", "what time is it", "current time")
        if (/(what|tell).*?time.*?(is it|right now|current|now)/.test(prompt) || prompt === 'current time' || prompt === 'what time is it' || prompt === 'time') {
            return generateCurrentTimeCard();
        }

        // Pattern 5: Current Date (e.g. "what is today's date", "what day is today", "what is the date today")
        if (/(today'?s?\s+date|date\s+today|what\s+day\s+is\s+today|what\s+day\s+is\s+it\s+today|what\s+is\s+the\s+date)/.test(prompt) || prompt === 'current date') {
            return generateCurrentDateCard();
        }

        // Pattern 6: Location Query (e.g. "what is my current location", "where am i right now")
        if (/what.*?my.*?current location|where am i|my location|where am i right now/.test(prompt)) {
            return await fetchUserLocationInfo();
        }

        return null;
    }

    // --- Real-time Streaming Prompt Handler ---
    async function sendPrompt(customText = null) {
        let rawText = customText || elements.promptInput.value.trim();
        if (!rawText && state.attachedFiles.length === 0) return;
        if (state.isGenerating) return;

        // Categorize attached files
        const imageFiles = state.attachedFiles.filter(f => f.isImage);
        const docFiles = state.attachedFiles.filter(f => !f.isImage);

        // Build User Display Message
        let displayParts = [];
        imageFiles.forEach(f => {
            displayParts.push(`![${escapeHtml(f.name)}](${f.content})`);
        });
        docFiles.forEach(f => {
            displayParts.push(`📄 **[Attached Document: ${escapeHtml(f.name)}]**`);
        });
        if (rawText) {
            displayParts.push(rawText);
        }
        const userDisplayContent = displayParts.join('\n\n');

        // Build Payload for Backend API
        const imagePayload = imageFiles.map(f => ({
            mime_type: f.type || 'image/png',
            data: f.content
        }));

        const filePayload = docFiles.map(f => ({
            filename: f.name,
            content_type: f.type,
            data: f.content,
            is_pdf: f.isPdf
        }));

        // Clear input box and attached files
        elements.promptInput.value = '';
        elements.promptInput.style.height = 'auto';
        state.attachedFiles = [];
        renderAttachmentPills();

        // Hide welcome container
        elements.welcomeContainer.style.display = 'none';
        elements.messagesFeed.style.display = 'flex';

        // Append User Message to UI
        appendMessageToUI('user', userDisplayContent);

        // Prepare Assistant row with typing indicator
        state.isGenerating = true;
        elements.sendBtn.disabled = true;

        const aiRow = document.createElement('div');
        aiRow.className = 'message-row assistant';
        aiRow.innerHTML = `
            <div class="avatar">
                <img src="/static/assets/nexora-ai-avatar.png?v=2.0" class="nexora-avatar-img" alt="NEXORA AI">
            </div>
            <div class="bubble">
                <div class="bubble-content">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        elements.messagesFeed.appendChild(aiRow);
        const bubbleContent = aiRow.querySelector('.bubble-content');
        scrollToBottom();

        // Check for Real-time intent (Weather, Time, Location, Date)
        if (rawText && imagePayload.length === 0 && filePayload.length === 0) {
            const realtimeResponse = await handleRealtimeIntent(rawText);
            if (realtimeResponse) {
                state.isGenerating = false;
                elements.sendBtn.disabled = false;
                bubbleContent.innerHTML = realtimeResponse;
                scrollToBottom();
                return;
            }
        }

        let accumulatedText = '';

        try {
            const clientHistory = state.messages.map(m => ({ role: m.role, content: m.content }));
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: state.currentChatId,
                    prompt: rawText || 'Tell me about this document',
                    history: clientHistory,
                    images: imagePayload.length > 0 ? imagePayload : undefined,
                    files: filePayload.length > 0 ? filePayload : undefined,
                    model: state.activeModel,
                    system_prompt: state.systemPrompt
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep last incomplete line

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;

                        try {
                            const eventData = JSON.parse(jsonStr);
                            if (eventData.type === 'meta') {
                                if (eventData.chat_id) {
                                    state.currentChatId = eventData.chat_id;
                                    renderChatList(elements.searchChatInput.value);
                                    await loadChats();
                                }
                            } else if (eventData.type === 'content') {
                                accumulatedText += eventData.content;
                                bubbleContent.innerHTML = formatMarkdown(accumulatedText);
                                attachCodeCopyListeners(aiRow);
                                scrollToBottom();
                            } else if (eventData.type === 'done') {
                                await loadChats();
                            }
                        } catch (parseErr) {
                            console.warn('SSE Parse error:', parseErr);
                        }
                    }
                }
            }

        } catch (err) {
            console.error('Streaming error:', err);
            bubbleContent.innerHTML = `<span style="color:#EF4444;">⚠️ Connection error: ${escapeHtml(err.message)}</span>`;
        } finally {
            state.isGenerating = false;
            elements.sendBtn.disabled = false;
        }
    }

    // --- Event Listeners Setup ---
    function setupEventListeners() {
        // Toggle Sidebar
        elements.toggleSidebarBtn.addEventListener('click', () => {
            elements.sidebar.classList.toggle('collapsed');
        });

        elements.mobileMenuBtn.addEventListener('click', () => {
            elements.sidebar.classList.toggle('collapsed');
        });

        // New Chat Button
        elements.newChatBtn.addEventListener('click', () => {
            resetToWelcomeScreen();
        });

        // Search Input Filter
        elements.searchChatInput.addEventListener('input', (e) => {
            renderChatList(e.target.value);
        });

        // File Attachment Click Listeners
        if (elements.attachBtn && elements.fileInput) {
            elements.attachBtn.addEventListener('click', () => {
                elements.fileInput.click();
            });
            elements.fileInput.addEventListener('change', handleFileSelection);
        }

        // Send Button & Textarea Enter Handler
        elements.sendBtn.addEventListener('click', () => sendPrompt());

        elements.promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendPrompt();
            }
        });

        // Textarea Auto-expand
        elements.promptInput.addEventListener('input', () => {
            elements.promptInput.style.height = 'auto';
            elements.promptInput.style.height = Math.min(elements.promptInput.scrollHeight, 180) + 'px';
        });

        // Starter Cards Click
        document.querySelectorAll('.starter-card').forEach(card => {
            card.addEventListener('click', () => {
                const action = card.dataset.action;
                const prompt = card.dataset.prompt;

                if (action === 'upload' || action === 'upload-doc') {
                    if (elements.fileInput) {
                        elements.fileInput.click();
                    }
                } else if (action === 'voice') {
                    const startVoiceModeBtn = document.getElementById('startVoiceModeBtn');
                    if (startVoiceModeBtn) {
                        startVoiceModeBtn.click();
                    }
                } else if (action === 'image-search') {
                    if (elements.promptInput) {
                        elements.promptInput.value = prompt || "Find images related to ";
                        elements.promptInput.focus();
                        const len = elements.promptInput.value.length;
                        elements.promptInput.setSelectionRange(len, len);
                    }
                } else if (prompt) {
                    if (elements.promptInput) {
                        elements.promptInput.value = prompt;
                        elements.promptInput.focus();
                    }
                }
            });
        });

        // Modals Logic
        elements.settingsBtn.addEventListener('click', () => {
            elements.modalGeminiKey.value = '';  // Never store API keys in the frontend
            elements.settingsModal.classList.add('active');
        });

        elements.closeSettingsModal.addEventListener('click', () => {
            elements.settingsModal.classList.remove('active');
        });

        elements.cancelSettingsBtn.addEventListener('click', () => {
            elements.settingsModal.classList.remove('active');
        });

        elements.saveSettingsBtn.addEventListener('click', async () => {
            const res = await apiFetch('/api/settings', {
                method: 'POST',
                body: JSON.stringify({
                    mongodb_uri: elements.modalMongoUri.value.trim() || undefined,
                    gemini_api_key: elements.modalGeminiKey.value.trim() || undefined
                })
            });

            if (res.status === 'success') {
                alert('Settings updated successfully!');
                elements.settingsModal.classList.remove('active');
                await checkHealth();
            }
        });

        elements.systemPromptBtn.addEventListener('click', () => {
            elements.systemPromptModal.classList.add('active');
        });

        elements.closeSystemModal.addEventListener('click', () => {
            elements.systemPromptModal.classList.remove('active');
        });

        elements.cancelSystemBtn.addEventListener('click', () => {
            elements.systemPromptModal.classList.remove('active');
        });

        elements.saveSystemBtn.addEventListener('click', async () => {
            state.systemPrompt = elements.systemPromptInput.value.trim();
            if (state.currentChatId) {
                await apiFetch(`/api/chats/${state.currentChatId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ system_prompt: state.systemPrompt })
                });
            }
            elements.systemPromptModal.classList.remove('active');
        });

        // User Account & Auth Listeners
        if (elements.authActionBtn) {
            elements.authActionBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (state.currentUser) {
                    if (confirm(`Logout from @${state.currentUser.username}?`)) {
                        await apiFetch('/api/auth/logout', { method: 'POST' });
                        localStorage.removeItem('ai_bot_token');
                        state.token = null;
                        state.currentUser = null;
                        renderUserProfile();
                    }
                } else {
                    openAuthModal('login');
                }
            });
        }

        if (elements.userAccountCard) {
            elements.userAccountCard.addEventListener('click', () => {
                if (!state.currentUser) {
                    openAuthModal('login');
                }
            });
        }

        if (elements.closeAuthModal) {
            elements.closeAuthModal.addEventListener('click', () => {
                elements.authModal.classList.remove('active');
            });
        }

        if (elements.tabLoginBtn && elements.tabRegisterBtn) {
            elements.tabLoginBtn.addEventListener('click', () => switchAuthTab('login'));
            elements.tabRegisterBtn.addEventListener('click', () => switchAuthTab('register'));
        }

        if (elements.loginForm) {
            elements.loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                elements.authErrorMsg.style.display = 'none';
                const emailOrUsername = elements.loginEmailInput.value.trim();
                const password = elements.loginPasswordInput.value;

                const res = await apiFetch('/api/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ email_or_username: emailOrUsername, password: password })
                });

                if (res.status === 'success' && res.token) {
                    localStorage.setItem('ai_bot_token', res.token);
                    state.token = res.token;
                    state.currentUser = res.user;
                    renderUserProfile();
                    elements.authModal.classList.remove('active');
                    elements.loginForm.reset();
                } else {
                    elements.authErrorMsg.textContent = res.detail || res.message || 'Login failed.';
                    elements.authErrorMsg.style.display = 'block';
                }
            });
        }

        if (elements.registerForm) {
            elements.registerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                elements.authErrorMsg.style.display = 'none';
                const username = elements.regUsernameInput.value.trim();
                const email = elements.regEmailInput.value.trim();
                const password = elements.regPasswordInput.value;

                const res = await apiFetch('/api/auth/register', {
                    method: 'POST',
                    body: JSON.stringify({ username: username, email: email, password: password })
                });

                if (res.status === 'success' && res.token) {
                    localStorage.setItem('ai_bot_token', res.token);
                    state.token = res.token;
                    state.currentUser = res.user;
                    renderUserProfile();
                    elements.authModal.classList.remove('active');
                    elements.registerForm.reset();
                } else {
                    elements.authErrorMsg.textContent = res.detail || res.message || 'Registration failed.';
                    elements.authErrorMsg.style.display = 'block';
                }
            });
        }
    }

    // --- Authentication Helpers ---
    async function checkAuthSession() {
        const savedToken = localStorage.getItem('ai_bot_token');
        if (savedToken) {
            state.token = savedToken;
            const res = await apiFetch('/api/auth/me');
            if (res && res.status === 'success' && res.user) {
                state.currentUser = res.user;
            } else {
                localStorage.removeItem('ai_bot_token');
                state.token = null;
                state.currentUser = null;
            }
        }
        renderUserProfile();
    }

    function renderUserProfile() {
        if (!elements.userAvatar) return;
        if (state.currentUser) {
            elements.userAvatar.src = state.currentUser.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${state.currentUser.username}`;
            elements.userName.textContent = state.currentUser.username;
            elements.userEmail.textContent = state.currentUser.email;
            elements.authActionBtn.title = "Logout";
            elements.authActionIcon.className = "fa-solid fa-arrow-right-from-bracket";
        } else {
            elements.userAvatar.src = "https://api.dicebear.com/7.x/bottts/svg?seed=guest";
            elements.userName.textContent = "Guest Developer";
            elements.userEmail.textContent = "Sign in to save history";
            elements.authActionBtn.title = "Sign In / Register";
            elements.authActionIcon.className = "fa-solid fa-right-to-bracket";
        }
    }

    function openAuthModal(mode = 'login') {
        elements.authErrorMsg.style.display = 'none';
        switchAuthTab(mode);
        elements.authModal.classList.add('active');
    }

    function switchAuthTab(tab) {
        if (tab === 'login') {
            elements.tabLoginBtn.classList.add('active');
            elements.tabRegisterBtn.classList.remove('active');
            elements.loginForm.style.display = 'block';
            elements.registerForm.style.display = 'none';
            elements.authModalTitle.textContent = 'Sign In to AI BOT';
        } else {
            elements.tabRegisterBtn.classList.add('active');
            elements.tabLoginBtn.classList.remove('active');
            elements.registerForm.style.display = 'block';
            elements.loginForm.style.display = 'none';
            elements.authModalTitle.textContent = 'Register New Account';
        }
    }

    // Helper: XSS escape
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Public App API for Voice Mode Integration
    window.MyChatApp = {
        getCurrentChatId: () => state.currentChatId,
        setCurrentChatId: (id) => { state.currentChatId = id; },
        appendMessage: (role, content) => {
            if (elements.welcomeContainer) elements.welcomeContainer.style.display = 'none';
            if (elements.messagesFeed) elements.messagesFeed.style.display = 'flex';
            const row = appendMessageToUI(role, content);
            return row;
        },
        loadChats: loadChats,
        getSystemPrompt: () => state.systemPrompt,
        getActiveModel: () => state.activeModel,
        handleRealtimeIntent: handleRealtimeIntent,
        sendPrompt: sendPrompt
    };

    // Start App
    init();
});
