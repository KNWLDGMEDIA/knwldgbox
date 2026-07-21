<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Send, Bot, User, Trash2 } from 'lucide-vue-next'
import { marked } from 'marked'

const { t } = useI18n()

const messages = ref([])
const userInput = ref('')
const isGenerating = ref(false)
const chatContainer = ref(null)

const selectedModel = ref('openrouter/free')
const availableModels = ref([
  { name: 'OpenRouter Free (Auto-Select)', value: 'openrouter/free' }
])

onMounted(async () => {
  // Try to get configured model from settings
  const savedSettings = localStorage.getItem('knwldg_api_settings')
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings)
      if (parsed.openrouter_model) {
        selectedModel.value = parsed.openrouter_model
      }
    } catch(e) {}
  }
  
  // Load models from OpenRouter
  try {
    const res = await fetch('https://openrouter.ai/api/v1/models')
    const json = await res.json()
    if (json && json.data) {
      const freeModels = json.data.filter(m => m.pricing && m.pricing.prompt === "0" && m.pricing.completion === "0")
      const dynamicModels = freeModels.map(m => ({
        name: m.name,
        value: m.id
      }))
      
      const existingValues = new Set(dynamicModels.map(m => m.value))
      availableModels.value = [
        ...dynamicModels.sort((a, b) => a.name.localeCompare(b.name)),
        ...availableModels.value.filter(m => !existingValues.has(m.value))
      ]
    }
  } catch (e) {
    console.error("Failed to load models", e)
  }
  
  // Load chat history
  const history = localStorage.getItem('knwldg_chat_history')
  if (history) {
    try {
      messages.value = JSON.parse(history)
      scrollToBottom()
    } catch(e) {}
  } else {
    // Initial welcome message
    messages.value.push({
      role: 'assistant',
      content: t('aiChatbot.welcomeMessage')
    })
  }
})

function saveHistory() {
  localStorage.setItem('knwldg_chat_history', JSON.stringify(messages.value))
}

function clearChat() {
  messages.value = [{
    role: 'assistant',
    content: t('aiChatbot.clearedMessage')
  }]
  saveHistory()
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || isGenerating.value) return
  
  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  saveHistory()
  scrollToBottom()
  
  isGenerating.value = true
  
  // Filter messages for API
  const apiMessages = messages.value.map(m => ({ role: m.role, content: m.content }))
  
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        messages: apiMessages,
        model: selectedModel.value
      })
    })
    
    const data = await res.json()
    if (res.ok && data.status === 'success') {
      messages.value.push({
        role: 'assistant',
        content: data.message.content
      })
    } else {
      messages.value.push({
        role: 'assistant',
        content: `**${t('aiChatbot.errorPrefix')}** ${data.detail || 'Failed to connect to AI'}`
      })
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: `**${t('aiChatbot.errorPrefix')}** ${e.message}`
    })
  } finally {
    isGenerating.value = false
    saveHistory()
    scrollToBottom()
  }
}
</script>

<template>
  <div class="chat-page">
    <div class="header-section flex justify-between items-start">
      <div>
        <h1 class="page-title">{{ $t('sidebar.aiChatbot') }}</h1>
        <p class="page-subtitle">{{ $t('aiChatbot.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <select v-model="selectedModel" class="model-select glass-panel">
          <option v-for="model in availableModels" :key="model.value" :value="model.value">
            {{ model.name }}
          </option>
        </select>
        <button class="icon-btn glass-panel text-red" @click="clearChat" :title="$t('common.delete')">
          <Trash2 size="18" />
        </button>
      </div>
    </div>

    <div class="chat-layout glass-panel">
      <div class="messages-container custom-scrollbar" ref="chatContainer">
        <div 
          v-for="(msg, idx) in messages" 
          :key="idx" 
          class="message-wrapper"
          :class="msg.role === 'user' ? 'is-user' : 'is-ai'"
        >
          <div class="avatar">
            <User v-if="msg.role === 'user'" size="18" />
            <Bot v-else size="18" class="text-orange" />
          </div>
          <div class="message-bubble">
            <div class="message-content markdown-body" v-if="msg.role === 'assistant'" v-html="marked(msg.content)"></div>
            <div class="message-content" v-else>{{ msg.content }}</div>
          </div>
        </div>
        
        <div v-if="isGenerating" class="message-wrapper is-ai">
          <div class="avatar"><Bot size="18" class="text-orange" /></div>
          <div class="message-bubble loading-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
      
      <div class="input-area">
        <textarea 
          v-model="userInput" 
          @keydown.enter.prevent="sendMessage"
          class="chat-input custom-scrollbar" 
          :placeholder="$t('aiChatbot.placeholder')"
          spellcheck="true"
          :disabled="isGenerating"
        ></textarea>
        <button class="send-btn" @click="sendMessage" :disabled="!userInput.trim() || isGenerating">
          <Send size="18" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-right: 8px;
}

.header-section {
  margin-bottom: 24px;
}

.page-title {
  font-size: 2rem;
  margin-bottom: 8px;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-select {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 8px 12px;
  font-size: 0.85rem;
  outline: none;
  max-width: 300px;
  cursor: pointer;
}

.model-select:focus {
  border-color: var(--accent-orange);
}

.icon-btn {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--accent-red);
}

.text-red { color: var(--accent-red); }
.text-orange { color: var(--accent-orange); }

.chat-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  overflow: hidden;
  margin-bottom: 16px;
}

.messages-container {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-wrapper {
  display: flex;
  gap: 16px;
  max-width: 80%;
}

.message-wrapper.is-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-wrapper.is-ai {
  align-self: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--overlay-10);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-bubble {
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  padding: 12px 16px;
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--text-main);
}

.is-user .message-bubble {
  background: rgba(var(--accent-rgb), 0.1);
  border-color: rgba(var(--accent-rgb), 0.3);
  white-space: pre-wrap;
}

.input-area {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  background: var(--overlay-5);
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  background: var(--bg-dark);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 12px;
  resize: none;
  outline: none;
  font-size: 0.95rem;
  min-height: 50px;
  max-height: 150px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: var(--accent-orange);
}

.send-btn {
  background: var(--accent-orange);
  color: #000;
  border: none;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity 0.2s;
}

.send-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.send-btn:disabled {
  background: var(--overlay-10);
  color: var(--text-muted);
  cursor: not-allowed;
}

.loading-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 24px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.markdown-body :deep(h1), 
.markdown-body :deep(h2), 
.markdown-body :deep(h3) {
  color: var(--accent-orange);
  margin-top: 12px;
  margin-bottom: 8px;
}

.markdown-body :deep(p) {
  margin-bottom: 12px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: var(--bg-dark);
  padding: 12px;
  border: 1px solid var(--border-color);
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-body :deep(code) {
  font-family: monospace;
  background: var(--bg-dark);
  padding: 2px 4px;
}

.markdown-body :deep(ul) {
  margin-left: 20px;
  list-style-type: disc;
}
</style>
