/**
 * NEXORA AI - Human-Like Conversational Voice Assistant Engine (voice.js) v6.0
 * ──────────────────────────────────────────────────────────────────────────
 * Conversational Enhancements:
 *   ① Human-like Conversational System Prompt & Personality (Adaptive length, friendly/calm tone)
 *   ② Context-aware multi-turn conversation memory with MongoDB synchronization
 *   ③ Multilingual & Hinglish Support (English, Hindi, Hinglish matching)
 *   ④ Natural Spoken Text Formatting (Markdown & list conversion to fluid spoken sentences)
 *   ⑤ High-Speed Streaming SSE Pipeline with Sentence Detection Buffer & Speech Queue
 *   ⑥ Instant Barge-in & Interruption Handling (AbortController + SpeechSynthesis.cancel)
 *   ⑦ Smart Conversational Location & Real-Time Intent Fallbacks
 *   ⑧ Clean Exit & Resource Cleanup (Mic audio track release)
 */

(function () {
    'use strict';

    // ─── Browser Capability Detection ────────────────────────────────────────
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const hasBrowserSTT     = !!SpeechRecognition;
    const hasBrowserTTS     = 'speechSynthesis' in window;

    // ─── Conversational Voice System Prompt Instruction ───────────────────────
    const CONVERSATIONAL_VOICE_SYSTEM_PROMPT = 
        "You are NEXORA AI, a friendly, intelligent, calm, confident, helpful, and natural human conversational assistant.\n\n" +
        "YOUR CORE GOAL:\n" +
        "Communicate with humans naturally, as if having a real face-to-face conversation with another smart person.\n\n" +
        "CRITICAL RULES FOR CONVERSATIONAL VOICE MODE:\n" +
        "1. NO ROBOTIC OR FORMAL PREAMBLES:\n" +
        "   - NEVER say: 'I am an AI language model', 'I am happy to assist you with your query', 'Please provide more information', 'Certainly! Here is a detailed answer to your question'.\n" +
        "   - Do NOT start every response with 'Sure!', 'Of course!', 'Certainly!', 'Absolutely!'. Vary your openers naturally or answer directly.\n\n" +
        "2. NATURAL CONVERSATIONAL LANGUAGE & TONE:\n" +
        "   - Sound friendly, warm, confident, and professional.\n" +
        "   - Use natural contractions (it's, that's, let's, don't, you're, I'm, we'll, who's, what's).\n" +
        "   - Use conversational phrases naturally when appropriate: 'Yeah...', 'Sure.', 'Right.', 'Exactly.', 'Actually...', 'That's a good question.', 'Got it.', 'Okay, I understand.', 'Let me explain that.', 'Here's the simple way to think about it.' (Do NOT overuse them).\n" +
        "   - Never repeat the user's question back to them.\n\n" +
        "3. ADAPTIVE RESPONSE LENGTH & CONCISENESS:\n" +
        "   - Short / Simple Question ('What's 2+2?', 'What is Python?') -> Short direct answer. For 'What is 2+2?', say 'Four.'. For 'What's Python?', give a 2-sentence simple overview. Do NOT generate a 500-word explanation unless asked ('explain in detail').\n" +
        "   - Casual Greetings ('Hey', 'Good morning', 'How are you?') -> Casual 1-sentence greeting ('Hey! What's up?', 'Good morning! How can I help?', 'I'm doing great! What are you working on today?').\n" +
        "   - Emotional / Personal ('I'm nervous about my interview') -> Empathetic and warm ('Yeah, interviews can definitely be stressful. But don't worry, we can practice together. I can ask you Python interview questions one by one and give you feedback.').\n" +
        "   - Celebration ('I got selected!') -> Enthusiastic and natural ('That's awesome! Congratulations! 🎉').\n" +
        "   - Detailed Request ('Explain recursion in detail', 'Step by step guide') -> Provide a detailed, clear explanation.\n\n" +
        "4. CONTEXT MEMORY & FOLLOW-UP HANDLING:\n" +
        "   - Remember the ongoing conversation context.\n" +
        "   - Resolve pronouns ('it', 'this', 'that', 'he', 'she', 'why', 'again', 'how so') seamlessly. (e.g. If user asked 'What is Python?' and then asks 'Why is it popular?', understand 'it' refers to Python. Never ask 'What are you referring to?').\n" +
        "   - If user asks to 'explain again' or 'I didn't understand', explain using a simpler real-world analogy (like Russian dolls for recursion or counting people in line), do NOT repeat the exact same previous words.\n" +
        "   - Handle short follow-ups ('Why?', 'Okay', 'Yes', 'No', 'What about AI?') naturally.\n\n" +
        "5. HUMAN-LIKE SPEECH & IMPERFECT GRAMMAR:\n" +
        "   - Understand imperfect grammar and informal queries ('what python', 'python kya hai', 'tell me python', 'wait what did you say', 'what is this machine learning thing').\n" +
        "   - If a query is genuinely ambiguous ('Tell me about Java'), ask a short natural clarification ('Sure. Do you mean Java the programming language, or JavaScript?').\n\n" +
        "6. LANGUAGE MATCHING (ENGLISH, HINDI, HINGLISH):\n" +
        "   - Match the user's language EXACTLY:\n" +
        "     * English -> Respond in natural English.\n" +
        "     * Hindi -> Respond in natural Hindi.\n" +
        "     * Hinglish -> Respond in natural Hinglish ('Python ek programming language hai jo kaafi easy aur beginner-friendly hai. Iska use AI, web development aur automation mein hota hai.').\n" +
        "   - Do not switch languages unnecessarily.\n\n" +
        "7. SPOKEN VOICE OUTPUT FORMATTING:\n" +
        "   - Speak in natural fluid sentences. Do NOT output raw Markdown symbols (no #, **, _, ``` code blocks, bullet points -, or 1. 2. 3. numbers).\n" +
        "   - Convert lists into spoken sentences ('First,... Second,... Also,...').\n" +
        "   - Never falsely claim to be a human, but speak naturally like one.";

    // ─── State Machine Constants ─────────────────────────────────────────────
    const VOICE_STATES = {
        IDLE:        'IDLE',
        LISTENING:   'LISTENING',
        PROCESSING:  'PROCESSING',
        SPEAKING:    'SPEAKING',
        INTERRUPTED: 'INTERRUPTED',
        MUTED:       'MUTED',
        ERROR:       'ERROR',
        ENDED:       'ENDED'
    };

    let currentState = VOICE_STATES.ENDED;
    let isVoiceModeActive = false;
    let isMuted = false;
    let preferredLanguage = 'en-IN';
    let speechRate = 1.0;
    let speechPitch = 1.0;
    let speechVolume = 1.0;
    let selectedVoiceURI = 'auto';

    // ─── Speech Recognition & Fetch Stream State ──────────────────────────────
    let recognitionInstance = null;
    let activeAudioStream = null;
    let activeFetchController = null;
    let isRecognitionStarting = false;
    let silenceTimer = null;
    let lastProcessedTranscript = '';
    let isProcessingAPI = false;

    // ─── Streaming Speech Queue State ─────────────────────────────────────────
    let speechQueue = [];
    let isSpeechActive = false;

    // ─── Speech Synthesis State ──────────────────────────────────────────────
    let currentUtterance = null;
    let preferredVoice = null;
    let availableVoices = [];

    // ─── DOM Element Cache ────────────────────────────────────────────────────
    const dom = {
        // Triggers
        startVoiceModeBtn:      document.getElementById('startVoiceModeBtn'),
        voiceMicBtn:            document.getElementById('voiceMicBtn'),
        voiceMicIcon:           document.getElementById('voiceMicIcon'),
        promptInput:            document.getElementById('promptInput'),

        // Voice Overlay & Stage
        voiceModeOverlay:       document.getElementById('voiceModeOverlay'),
        voiceStateBadge:        document.getElementById('voiceStateBadge'),
        voiceStateDot:          document.getElementById('voiceStateDot'),
        voiceStateText:         document.getElementById('voiceStateText'),
        voiceStatusCaption:     document.getElementById('voiceStatusCaption'),
        voiceStage:             document.querySelector('.voice-mode-stage'),

        // Action Buttons & Controls
        voiceMuteToggleBtn:     document.getElementById('voiceMuteToggleBtn'),
        voiceMuteIcon:          document.getElementById('voiceMuteIcon'),
        voiceSettingsToggleBtn: document.getElementById('voiceSettingsToggleBtn'),
        voiceSettingsDrawer:    document.getElementById('voiceSettingsDrawer'),
        vmLangSelect:           document.getElementById('vmLangSelect'),
        vmVoiceSelect:          document.getElementById('vmVoiceSelect'),
        vmSpeedSelect:          document.getElementById('vmSpeedSelect'),
        vmPitchSelect:          document.getElementById('vmPitchSelect'),
        vmVolumeSelect:         document.getElementById('vmVolumeSelect'),
        closeVoiceModeBtn:      document.getElementById('closeVoiceModeBtn'),
        endVoiceModeBtn:        document.getElementById('endVoiceModeBtn'),
        voiceStageActions:      document.getElementById('voiceStageActions'),
        voiceStopSpeakingBtn:   document.getElementById('voiceStopSpeakingBtn'),
        voiceInterruptBtn:      document.getElementById('voiceInterruptBtn'),

        // Subtitles / Transcript Elements
        voiceUserRow:           document.getElementById('voiceUserRow'),
        voiceUserText:          document.getElementById('voiceUserText'),
        voiceAiRow:             document.getElementById('voiceAiRow'),
        voiceAiText:            document.getElementById('voiceAiText'),

        // Toast / Fallback Elements
        aiSpeakingToast:        document.getElementById('aiSpeakingToast'),
        aiSpeakingStopBtn:      document.getElementById('aiSpeakingStopBtn')
    };

    // ─── Load & Populate Voices ──────────────────────────────────────────────
    function populateVoiceList() {
        if (!hasBrowserTTS) return;
        availableVoices = window.speechSynthesis.getVoices() || [];
        
        if (dom.vmVoiceSelect) {
            const currentSelected = dom.vmVoiceSelect.value;
            dom.vmVoiceSelect.innerHTML = '<option value="auto">Auto Select (Default)</option>';
            
            availableVoices.forEach((voice) => {
                const option = document.createElement('option');
                option.value = voice.voiceURI;
                option.textContent = `${voice.name} (${voice.lang})`;
                if (voice.voiceURI === currentSelected) option.selected = true;
                dom.vmVoiceSelect.appendChild(option);
            });
        }
        selectBestVoice();
    }

    function selectBestVoice() {
        if (!hasBrowserTTS || availableVoices.length === 0) return;

        if (selectedVoiceURI !== 'auto') {
            const matched = availableVoices.find(v => v.voiceURI === selectedVoiceURI);
            if (matched) {
                preferredVoice = matched;
                return;
            }
        }

        const lang = preferredLanguage.toLowerCase();
        preferredVoice =
            availableVoices.find(v => v.lang.toLowerCase() === lang) ||
            availableVoices.find(v => v.lang.toLowerCase().startsWith(lang.slice(0, 2))) ||
            availableVoices.find(v => v.name.includes('Google') && v.lang.includes('en')) ||
            availableVoices.find(v => v.lang.includes('en')) ||
            availableVoices[0] ||
            null;
    }

    if (hasBrowserTTS) {
        populateVoiceList();
        window.speechSynthesis.onvoiceschanged = populateVoiceList;
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  STATE MACHINE & TRANSITION MANAGEMENT
    // ══════════════════════════════════════════════════════════════════════════

    function transitionTo(newState, metaData = {}) {
        if (currentState === VOICE_STATES.ENDED && newState !== VOICE_STATES.IDLE && newState !== VOICE_STATES.LISTENING && newState !== VOICE_STATES.ENDED) {
            return;
        }

        console.log(`[VoiceMode] State Transition: ${currentState} ➔ ${newState}`, metaData);
        currentState = newState;

        // Sync mic button UI
        setMicBtnState(newState === VOICE_STATES.LISTENING);

        // Reset stage classes
        if (dom.voiceStage) dom.voiceStage.className = 'voice-mode-stage';
        if (dom.voiceStateBadge) dom.voiceStateBadge.className = 'voice-state-badge';

        switch (newState) {
            case VOICE_STATES.LISTENING:
                updateStateUI('listening', '🎤 Listening...', 'Listening... Speak now');
                if (dom.voiceStageActions) dom.voiceStageActions.style.display = 'none';
                startListeningInternal();
                break;

            case VOICE_STATES.PROCESSING:
                updateStateUI('processing', '🧠 Thinking...', 'NEXORA AI is thinking...');
                if (dom.voiceStageActions) dom.voiceStageActions.style.display = 'none';
                stopSpeechRecognition();
                break;

            case VOICE_STATES.SPEAKING:
                updateStateUI('speaking', '🔊 Speaking...', 'NEXORA AI is responding...');
                if (dom.voiceStageActions) dom.voiceStageActions.style.display = 'flex';
                // Keep STT listening during SPEAKING to enable instant user barge-in!
                startListeningInternal();
                break;

            case VOICE_STATES.INTERRUPTED:
                updateStateUI('listening', '🎤 Listening...', 'Listening...');
                if (dom.voiceStageActions) dom.voiceStageActions.style.display = 'none';
                resetSpeechStreamAndQueue();
                startListeningInternal();
                break;

            case VOICE_STATES.MUTED:
                updateStateUI('muted', '🔇 Muted', 'Audio output muted');
                break;

            case VOICE_STATES.ERROR:
                updateStateUI('error', '⚠️ Error', metaData.message || 'An error occurred');
                if (dom.voiceStageActions) dom.voiceStageActions.style.display = 'none';
                stopSpeechRecognition();
                resetSpeechStreamAndQueue();
                break;

            case VOICE_STATES.ENDED:
                updateStateUI('ended', 'Ended', 'Voice Mode Ended');
                stopSpeechRecognition();
                resetSpeechStreamAndQueue();
                stopAudioStream();
                hideVoiceModeOverlay();
                break;

            default:
                break;
        }
    }

    function updateStateUI(badgeClass, badgeText, captionText) {
        if (dom.voiceStage) dom.voiceStage.classList.add(badgeClass);
        if (dom.voiceStateBadge) dom.voiceStateBadge.classList.add(badgeClass);
        if (dom.voiceStateText) dom.voiceStateText.textContent = badgeText;
        if (dom.voiceStatusCaption) dom.voiceStatusCaption.textContent = captionText;
    }

    function setMicBtnState(isListening) {
        if (!dom.voiceMicBtn) return;
        if (isListening) {
            dom.voiceMicBtn.classList.add('listening');
            if (dom.voiceMicIcon) dom.voiceMicIcon.className = 'fa-solid fa-microphone-slash';
            dom.voiceMicBtn.title = 'Stop voice mode';
        } else {
            dom.voiceMicBtn.classList.remove('listening');
            if (dom.voiceMicIcon) dom.voiceMicIcon.className = 'fa-solid fa-microphone';
            dom.voiceMicBtn.title = 'Voice Mode';
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  VOICE MODE START / EXIT & PERMISSION HANDLING
    // ══════════════════════════════════════════════════════════════════════════

    function startVoiceMode() {
        if (!hasBrowserSTT) {
            alert('Speech recognition is not supported by this browser. Please use a supported browser like Google Chrome or Microsoft Edge.');
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then((stream) => {
                activeAudioStream = stream;
                resetSpeechStreamAndQueue();
                isVoiceModeActive = true;
                showVoiceModeOverlay();
                lastProcessedTranscript = '';
                isProcessingAPI = false;

                initSpeechRecognition();
                transitionTo(VOICE_STATES.LISTENING);
            })
            .catch((err) => {
                console.error('[VoiceMode] Microphone permission error:', err);
                alert('Microphone access is required for Voice Mode. Please allow microphone access in your browser settings and try again.');
                transitionTo(VOICE_STATES.ERROR, { message: 'Microphone access denied' });
            });
    }

    function endVoiceMode() {
        isVoiceModeActive = false;
        transitionTo(VOICE_STATES.ENDED);
    }

    function stopAudioStream() {
        if (activeAudioStream) {
            try {
                activeAudioStream.getTracks().forEach(track => track.stop());
            } catch (e) {
                console.warn('[VoiceStream] Error stopping audio tracks:', e);
            }
            activeAudioStream = null;
        }
    }

    function showVoiceModeOverlay() {
        if (dom.voiceModeOverlay) {
            dom.voiceModeOverlay.classList.add('active');
        }
        if (dom.voiceUserText) dom.voiceUserText.textContent = 'Listening... Speak now';
        if (dom.voiceAiRow) dom.voiceAiRow.style.display = 'none';
        if (dom.voiceAiText) dom.voiceAiText.textContent = '';
    }

    function hideVoiceModeOverlay() {
        if (dom.voiceModeOverlay) {
            dom.voiceModeOverlay.classList.remove('active');
        }
        if (dom.voiceSettingsDrawer) {
            dom.voiceSettingsDrawer.style.display = 'none';
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  SPEECH RECOGNITION (STT) ENGINE
    // ══════════════════════════════════════════════════════════════════════════

    function initSpeechRecognition() {
        if (recognitionInstance) return;

        try {
            recognitionInstance = new SpeechRecognition();
            recognitionInstance.continuous = false; // single phrase per recognition session
            recognitionInstance.interimResults = true; // show live speech results
            recognitionInstance.maxAlternatives = 1;
            recognitionInstance.lang = preferredLanguage;

            recognitionInstance.onstart = () => {
                isRecognitionStarting = false;
                console.log('[VoiceSTT] Recognition started.');
            };

            recognitionInstance.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }

                const currentText = (finalTranscript || interimTranscript).trim();

                // User Interrupt / Barge-in: if user starts speaking while AI is speaking
                if (currentState === VOICE_STATES.SPEAKING && currentText.length > 2) {
                    console.log('[VoiceMode] User barge-in detected! Stopping AI speech...');
                    resetSpeechStreamAndQueue();
                    transitionTo(VOICE_STATES.INTERRUPTED);
                }

                if (currentText) {
                    if (dom.voiceUserText) dom.voiceUserText.textContent = `"${currentText}"`;
                    if (dom.voiceUserRow) dom.voiceUserRow.style.display = 'flex';
                    if (dom.promptInput) {
                        dom.promptInput.value = currentText;
                        dom.promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }

                // If final transcript is received, IMMEDIATELY submit without waiting!
                if (finalTranscript.trim()) {
                    if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
                    handleFinalUserSpeech(finalTranscript.trim());
                } else if (interimTranscript.trim().length > 3) {
                    resetSilenceTimer(interimTranscript.trim());
                }
            };

            recognitionInstance.onerror = (event) => {
                isRecognitionStarting = false;
                console.warn('[VoiceSTT] Error event:', event.error);

                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    alert('Microphone access is required for Voice Mode. Please allow microphone access in your browser settings and try again.');
                    endVoiceMode();
                    return;
                }

                if (event.error === 'no-speech') {
                    if (isVoiceModeActive && currentState === VOICE_STATES.LISTENING) {
                        restartListeningDebounced();
                    }
                    return;
                }

                if (event.error === 'aborted') return;

                if (isVoiceModeActive && currentState === VOICE_STATES.LISTENING) {
                    restartListeningDebounced();
                }
            };

            recognitionInstance.onend = () => {
                isRecognitionStarting = false;
                console.log('[VoiceSTT] Recognition ended. Current state:', currentState);

                // Auto restart listening loop if still active & in LISTENING or SPEAKING state
                if (isVoiceModeActive && (currentState === VOICE_STATES.LISTENING || currentState === VOICE_STATES.SPEAKING) && !isProcessingAPI) {
                    restartListeningDebounced();
                }
            };

        } catch (e) {
            console.error('[VoiceSTT] Initialization error:', e);
        }
    }

    function startListeningInternal() {
        if (!recognitionInstance) initSpeechRecognition();
        if (!recognitionInstance) return;

        if (isRecognitionStarting) return;

        try {
            recognitionInstance.lang = preferredLanguage;
            isRecognitionStarting = true;
            recognitionInstance.start();
        } catch (e) {
            isRecognitionStarting = false;
            if (e.name === 'InvalidStateError') {
                console.log('[VoiceSTT] Recognition already running.');
            } else {
                console.warn('[VoiceSTT] start() error:', e);
            }
        }
    }

    function stopSpeechRecognition() {
        if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
        if (recognitionInstance) {
            try {
                recognitionInstance.stop();
            } catch (_) {}
        }
        isRecognitionStarting = false;
    }

    function restartListeningDebounced() {
        setTimeout(() => {
            if (isVoiceModeActive && (currentState === VOICE_STATES.LISTENING || currentState === VOICE_STATES.SPEAKING)) {
                startListeningInternal();
            }
        }, 200);
    }

    function resetSilenceTimer(text) {
        if (silenceTimer) clearTimeout(silenceTimer);
        if (!text || text.length < 3) return;

        // Auto trigger fallback if user pauses after speaking without explicit final event
        silenceTimer = setTimeout(() => {
            if (currentState === VOICE_STATES.LISTENING && text && !isProcessingAPI) {
                handleFinalUserSpeech(text);
            }
        }, 1400);
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  STREAMING API INTEGRATION & SENTENCE-BASED TTS PIPELINE
    // ══════════════════════════════════════════════════════════════════════════

    async function handleFinalUserSpeech(userText) {
        if (!userText || isProcessingAPI || userText === lastProcessedTranscript) return;

        lastProcessedTranscript = userText;
        isProcessingAPI = true;
        if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }

        // Abort previous stream & clear speech queue
        resetSpeechStreamAndQueue();

        transitionTo(VOICE_STATES.PROCESSING);

        // 1. Sync User Message to main chat feed
        if (window.MyChatApp && window.MyChatApp.appendMessage) {
            window.MyChatApp.appendMessage('user', userText);
        }

        // 2. Check for Real-time intent (Weather, Time, Location, Date)
        if (window.MyChatApp && window.MyChatApp.handleRealtimeIntent) {
            try {
                const realtimeCardHTML = await window.MyChatApp.handleRealtimeIntent(userText);
                if (realtimeCardHTML) {
                    isProcessingAPI = false;

                    // Append real-time card to main feed
                    window.MyChatApp.appendMessage('assistant', realtimeCardHTML);

                    // Spoken representation
                    const spokenText = prepareTextForSpeech(realtimeCardHTML);
                    if (dom.voiceAiText) dom.voiceAiText.textContent = spokenText;
                    if (dom.voiceAiRow) dom.voiceAiRow.style.display = 'flex';

                    enqueueSentence(spokenText);
                    return;
                }
            } catch (err) {
                console.warn('[VoiceMode] Realtime intent error:', err);
            }
        }

        // 3. Prepare AI Request with Conversational System Prompt
        const activeModel = window.MyChatApp ? window.MyChatApp.getActiveModel() : 'gemini-2.5-flash';
        const currentChatId = window.MyChatApp ? window.MyChatApp.getCurrentChatId() : null;
        const baseSystemPrompt = window.MyChatApp ? window.MyChatApp.getSystemPrompt() : '';
        const fullVoiceSystemPrompt = (baseSystemPrompt ? baseSystemPrompt + "\n\n" : "") + CONVERSATIONAL_VOICE_SYSTEM_PROMPT;

        console.log('[VoiceMode] VOICE TRANSCRIPT:', userText);
        console.log('[VoiceMode] API REQUEST:', '/api/chat/stream', { model: activeModel, chat_id: currentChatId });

        // Create AbortController for active streaming fetch
        activeFetchController = new AbortController();

        let accumulatedText = '';
        let unspokenBuffer = '';

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: activeFetchController.signal,
                body: JSON.stringify({
                    chat_id: currentChatId,
                    prompt: userText,
                    model: activeModel,
                    system_prompt: fullVoiceSystemPrompt
                })
            });

            console.log('[VoiceMode] API STATUS:', response.status);

            if (!response.ok) {
                const errBody = await response.text().catch(() => '');
                console.error('[VoiceMode] API ERROR RESPONSE:', errBody);
                throw new Error(`HTTP error ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let sseBuffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                sseBuffer += decoder.decode(value, { stream: true });
                const lines = sseBuffer.split('\n');
                sseBuffer = lines.pop(); // Keep last incomplete line

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;

                        try {
                            const eventData = JSON.parse(jsonStr);
                            if (eventData.type === 'meta') {
                                if (eventData.chat_id && window.MyChatApp) {
                                    window.MyChatApp.setCurrentChatId(eventData.chat_id);
                                    window.MyChatApp.loadChats();
                                }
                            } else if (eventData.type === 'content') {
                                const chunk = eventData.content;
                                accumulatedText += chunk;
                                unspokenBuffer += chunk;

                                // Update Voice Mode overlay subtitle transcript in real-time
                                if (dom.voiceAiText) dom.voiceAiText.textContent = accumulatedText;
                                if (dom.voiceAiRow) dom.voiceAiRow.style.display = 'flex';
                                if (dom.promptInput) dom.promptInput.value = '';

                                // Process sentence boundaries in unspokenBuffer
                                unspokenBuffer = processUnspokenBuffer(unspokenBuffer, false);
                            } else if (eventData.type === 'done') {
                                if (window.MyChatApp) window.MyChatApp.loadChats();
                            }
                        } catch (parseErr) {
                            console.warn('[VoiceStream] SSE Parse error:', parseErr);
                        }
                    }
                }
            }

            // Flush remaining buffer at end of stream
            if (unspokenBuffer.trim()) {
                processUnspokenBuffer(unspokenBuffer, true);
            }

            console.log('[VoiceMode] AI RESPONSE RECEIVED:', accumulatedText.slice(0, 100) + '...');

            // Sync complete accumulated text to main chat UI feed
            if (accumulatedText.trim() && window.MyChatApp && window.MyChatApp.appendMessage) {
                window.MyChatApp.appendMessage('assistant', accumulatedText);
            }

        } catch (err) {
            const isAbort = err.name === 'AbortError' || err.name === 'DOMException' || (err.message && err.message.toLowerCase().includes('aborted'));
            if (isAbort) {
                console.log('[VoiceStream] Stream fetch aborted by user interrupt or state transition.');
            } else {
                console.error('[NEXORA Voice API Error]', {
                    url: '/api/chat/stream',
                    errorName: err.name,
                    message: err.message || err
                });
                const errText = "I couldn't connect to NEXORA AI right now. Please check your connection and try again.";
                enqueueSentence(errText);
            }
        } finally {
            isProcessingAPI = false;
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  STREAMING TTS SENTENCE BUFFER & QUEUE ENGINE
    // ══════════════════════════════════════════════════════════════════════════

    function processUnspokenBuffer(buffer, isFinalChunk = false) {
        if (!buffer) return '';

        // Match sentence terminators: . ! ? ; \n
        const sentenceEndRegex = /([.!?;\n]+)/;
        let textToScan = buffer;
        let match;

        while ((match = sentenceEndRegex.exec(textToScan)) !== null) {
            const endIdx = match.index + match[0].length;
            const sentenceCandidate = textToScan.slice(0, endIdx).trim();
            textToScan = textToScan.slice(endIdx);

            const cleanSentence = prepareTextForSpeech(sentenceCandidate);
            if (cleanSentence && cleanSentence.length > 1) {
                enqueueSentence(cleanSentence);
            }
        }

        if (isFinalChunk && textToScan.trim()) {
            const cleanSentence = prepareTextForSpeech(textToScan.trim());
            if (cleanSentence && cleanSentence.length > 1) {
                enqueueSentence(cleanSentence);
            }
            textToScan = '';
        }

        return textToScan;
    }

    function enqueueSentence(sentenceText) {
        if (!sentenceText) return;
        speechQueue.push(sentenceText);

        if (!isSpeechActive) {
            speakNextInQueue();
        }
    }

    function speakNextInQueue() {
        if (!isVoiceModeActive) {
            speechQueue = [];
            isSpeechActive = false;
            return;
        }

        if (speechQueue.length === 0) {
            isSpeechActive = false;
            // If API stream has completed and queue is empty, auto-return to LISTENING!
            if (!isProcessingAPI && currentState === VOICE_STATES.SPEAKING) {
                console.log('[VoiceTTS] All queued sentences spoken. Returning to LISTENING.');
                transitionTo(VOICE_STATES.LISTENING);
            }
            return;
        }

        isSpeechActive = true;
        const nextSentence = speechQueue.shift();

        if (isMuted) {
            transitionTo(VOICE_STATES.MUTED);
            setTimeout(() => {
                isSpeechActive = false;
                speakNextInQueue();
            }, 1500);
            return;
        }

        // IMMEDIATELY transition state to SPEAKING as soon as sentence 1 begins!
        if (currentState !== VOICE_STATES.SPEAKING) {
            transitionTo(VOICE_STATES.SPEAKING);
        }

        if (!hasBrowserTTS) {
            setTimeout(() => {
                isSpeechActive = false;
                speakNextInQueue();
            }, 2500);
            return;
        }

        currentUtterance = new SpeechSynthesisUtterance(nextSentence);
        currentUtterance.rate = speechRate;
        currentUtterance.pitch = speechPitch;
        currentUtterance.volume = speechVolume;

        selectBestVoice();
        if (preferredVoice) {
            currentUtterance.voice = preferredVoice;
        }

        currentUtterance.onend = () => {
            currentUtterance = null;
            isSpeechActive = false;
            // Speak next sentence in queue immediately
            speakNextInQueue();
        };

        currentUtterance.onerror = (e) => {
            console.warn('[VoiceTTS] Utterance error:', e);
            currentUtterance = null;
            isSpeechActive = false;
            speakNextInQueue();
        };

        window.speechSynthesis.speak(currentUtterance);
    }

    function resetSpeechStreamAndQueue() {
        if (activeFetchController) {
            try { activeFetchController.abort(); } catch (_) {}
            activeFetchController = null;
        }
        stopTTS();
        speechQueue = [];
        isSpeechActive = false;
        isProcessingAPI = false;
        lastProcessedTranscript = '';
    }

    function stopTTS() {
        if (hasBrowserTTS && window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }
        currentUtterance = null;
    }

    function prepareTextForSpeech(raw) {
        if (!raw) return '';

        let clean = raw
            // Strip HTML elements
            .replace(/<[^>]*>/g, ' ')
            // Convert numbered lists into natural spoken sentences
            .replace(/^\s*1\.\s+(.+)$/gm, 'First, $1.')
            .replace(/^\s*2\.\s+(.+)$/gm, 'Second, $1.')
            .replace(/^\s*3\.\s+(.+)$/gm, 'Third, $1.')
            .replace(/^\s*4\.\s+(.+)$/gm, 'Fourth, $1.')
            .replace(/^\s*5\.\s+(.+)$/gm, 'Fifth, $1.')
            .replace(/^\s*\d+\.\s+(.+)$/gm, 'Also, $1.')
            // Convert bullet points into natural spoken sentences
            .replace(/^\s*[-*+]\s+(.+)$/gm, 'Also, $1.')
            // Remove markdown code blocks
            .replace(/```[\s\S]*?```/g, ' Code snippet generated in chat. ')
            .replace(/`[^`]+`/g, ' ')
            .replace(/!\[.*?\]\(.*?\)/g, ' ')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/#{1,6}\s+/g, '')
            .replace(/[*_~]{1,3}([^*_~\n]+)[*_~]{1,3}/g, '$1')
            .replace(/>\s+/g, '')
            .replace(/\\\mathbf\{[^}]*\}/g, '')
            .replace(/\$\$/g, '')
            .replace(/\n{2,}/g, '. ')
            .replace(/\n/g, ' ')
            .replace(/\s{2,}/g, ' ')
            .trim();

        return clean;
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  EVENT LISTENERS & BINDINGS
    // ══════════════════════════════════════════════════════════════════════════

    function bindEvents() {
        // Navbar Voice Mode Button
        if (dom.startVoiceModeBtn) {
            dom.startVoiceModeBtn.addEventListener('click', () => {
                if (isVoiceModeActive) endVoiceMode();
                else startVoiceMode();
            });
        }

        // Input Capsule Mic Button
        if (dom.voiceMicBtn) {
            dom.voiceMicBtn.addEventListener('click', () => {
                if (isVoiceModeActive || currentState === VOICE_STATES.LISTENING) {
                    endVoiceMode();
                } else {
                    startVoiceMode();
                }
            });
        }

        // End Conversation & Close Buttons
        if (dom.closeVoiceModeBtn) {
            dom.closeVoiceModeBtn.addEventListener('click', endVoiceMode);
        }
        if (dom.endVoiceModeBtn) {
            dom.endVoiceModeBtn.addEventListener('click', endVoiceMode);
        }

        // Stop Speaking Button
        if (dom.voiceStopSpeakingBtn) {
            dom.voiceStopSpeakingBtn.addEventListener('click', () => {
                if (currentState === VOICE_STATES.SPEAKING) {
                    resetSpeechStreamAndQueue();
                    transitionTo(VOICE_STATES.LISTENING);
                }
            });
        }

        // Tap to Interrupt Button
        if (dom.voiceInterruptBtn) {
            dom.voiceInterruptBtn.addEventListener('click', () => {
                if (currentState === VOICE_STATES.SPEAKING) {
                    resetSpeechStreamAndQueue();
                    transitionTo(VOICE_STATES.LISTENING);
                }
            });
        }

        // Mute / Unmute Toggle
        if (dom.voiceMuteToggleBtn) {
            dom.voiceMuteToggleBtn.addEventListener('click', () => {
                isMuted = !isMuted;
                if (dom.voiceMuteToggleBtn) dom.voiceMuteToggleBtn.classList.toggle('muted', isMuted);
                if (dom.voiceMuteIcon) {
                    dom.voiceMuteIcon.className = isMuted ? 'fa-solid fa-volume-xmark' : 'fa-solid fa-volume-high';
                }
                if (isMuted && currentState === VOICE_STATES.SPEAKING) {
                    resetSpeechStreamAndQueue();
                    transitionTo(VOICE_STATES.MUTED);
                }
            });
        }

        // Settings Drawer Toggle
        if (dom.voiceSettingsToggleBtn && dom.voiceSettingsDrawer) {
            dom.voiceSettingsToggleBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVis = dom.voiceSettingsDrawer.style.display === 'flex';
                dom.voiceSettingsDrawer.style.display = isVis ? 'none' : 'flex';
            });
        }

        // Language Selector
        if (dom.vmLangSelect) {
            dom.vmLangSelect.addEventListener('change', (e) => {
                preferredLanguage = e.target.value;
                selectBestVoice();
            });
        }

        // Voice Selector
        if (dom.vmVoiceSelect) {
            dom.vmVoiceSelect.addEventListener('change', (e) => {
                selectedVoiceURI = e.target.value;
                selectBestVoice();
            });
        }

        // Speed Selector
        if (dom.vmSpeedSelect) {
            dom.vmSpeedSelect.addEventListener('change', (e) => {
                speechRate = parseFloat(e.target.value) || 1.0;
            });
        }

        // Pitch Selector
        if (dom.vmPitchSelect) {
            dom.vmPitchSelect.addEventListener('change', (e) => {
                speechPitch = parseFloat(e.target.value) || 1.0;
            });
        }

        // Volume Selector
        if (dom.vmVolumeSelect) {
            dom.vmVolumeSelect.addEventListener('change', (e) => {
                speechVolume = parseFloat(e.target.value) || 1.0;
            });
        }

        // Keyboard Escape Key to exit Voice Mode
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isVoiceModeActive) {
                endVoiceMode();
            }
        });

        // Close Drawer when clicking outside
        document.addEventListener('click', (e) => {
            if (dom.voiceSettingsDrawer && !e.target.closest('#voiceSettingsDrawer') && !e.target.closest('#voiceSettingsToggleBtn')) {
                dom.voiceSettingsDrawer.style.display = 'none';
            }
        });

        window.addEventListener('beforeunload', () => {
            resetSpeechStreamAndQueue();
            stopSpeechRecognition();
            stopAudioStream();
        });
    }

    // Initialize Event Bindings
    bindEvents();

    // Export Public Voice Assistant API
    window.VoiceAssistant = {
        startVoiceMode,
        endVoiceMode,
        isVoiceModeActive: () => isVoiceModeActive,
        getCurrentState: () => currentState
    };

    console.log('[VoiceMode] Human-Like Conversational Voice Assistant Engine v6.0 initialized.');
})();
