<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { MessageCircle, Play, Pause, Trash2, Image as ImageIcon, X } from 'lucide-vue-next'
import { apiService } from '../services/api'

const { t } = useI18n()

const props = defineProps({
  config: Object
})

const emit = defineEmits(['update-config', 'update-data'])

const channelName = ref(props.config.channel || '')
const isMonitoring = ref(props.config.active !== undefined ? props.config.active : false)
const messages = ref([])
const ws = ref(null)
const statusMsg = ref('')
const activeMediaUrl = ref(null)
const activeMediaType = ref('photo')
let hoverTimer = null
const mouseX = ref(0)
const mouseY = ref(0)

function handleMouseMove(event) {
  mouseX.value = event.clientX
  mouseY.value = event.clientY
}

function openMessageLink(channel, id) {
  const cleanChannel = channel.replace('@', '')
  window.open(`https://t.me/${cleanChannel}/${id}`, '_blank')
}

function handleMouseEnter(channel, msg) {
  if (!msg.has_media) return
  // Add a small delay so we don't spam downloads if the user just moves the mouse across the screen
  hoverTimer = setTimeout(() => {
    activeMediaType.value = msg.media_type || 'photo'
    activeMediaUrl.value = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/telegram/media/${channel}/${msg.id}`
  }, 400)
}

function handleMouseLeave() {
  if (hoverTimer) {
    clearTimeout(hoverTimer)
    hoverTimer = null
  }
  activeMediaUrl.value = null
}

// Load messages from localStorage when channel changes
function loadMessages() {
  if (!channelName.value) return
  const saved = localStorage.getItem(`knwldg_tg_${channelName.value}`)
  if (saved) {
    try {
      messages.value = JSON.parse(saved)
    } catch (e) {}
  } else {
    messages.value = []
  }
  emit('update-data', { type: 'telegram', source: channelName.value, items: messages.value })
}

// Save messages to localStorage
function saveMessages() {
  if (!channelName.value) return
  localStorage.setItem(`knwldg_tg_${channelName.value}`, JSON.stringify(messages.value))
  emit('update-data', { type: 'telegram', source: channelName.value, items: messages.value })
}

function connectWebSocket() {
  ws.value = apiService.createTelegramWebSocket()

  ws.value.onopen = () => {
    if (channelName.value) {
      statusMsg.value = t('telegramMonitor.connecting')
      ws.value.send(JSON.stringify({ action: 'subscribe', channel: channelName.value }))
    }
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)

    // Ignore system connection messages from history save
    if (data.author !== 'System') {
      statusMsg.value = '' // Clear status on real message
      // Don't add if we already have it (prevent duplicates on refresh if backend resends)
      if (!messages.value.some(m => m.id === data.id)) {
        messages.value.push(data)
        messages.value.sort((a, b) => b.id - a.id)
        if (messages.value.length > 50) {
          // Since we sort descending, we remove from the end (oldest)
          messages.value.pop()
        }
        saveMessages()
      }
    } else {
      // Update status string instead of polluting the feed
      statusMsg.value = data.text
    }
  }
}

function clearHistory() {
  messages.value = []
  if (channelName.value) {
    localStorage.removeItem(`knwldg_tg_${channelName.value}`)
  }
  emit('update-data', { type: 'telegram', source: channelName.value, items: [] })
}

function toggleMonitor() {
  if (channelName.value.trim() === '') return

  isMonitoring.value = !isMonitoring.value

  if (isMonitoring.value) {
    emit('update-config', { channel: channelName.value, active: true })
    loadMessages()
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
    } else {
      ws.value.send(JSON.stringify({ action: 'subscribe', channel: channelName.value }))
    }
  } else {
    emit('update-config', { channel: channelName.value, active: false })
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ action: 'unsubscribe', channel: channelName.value }))
    }
  }
}

onMounted(() => {
  if (isMonitoring.value) {
    loadMessages()
    connectWebSocket()
  }
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<template>
  <div class="widget-block glass-panel">
    <!-- Block Header -->
    <div class="block-header">
      <div class="block-title">
        <MessageCircle size="18" class="text-orange" />
        <h3>{{ t('telegramMonitor.title') }}</h3>
      </div>
    </div>

    <!-- Block Config / Input -->
    <div class="block-config" v-if="!isMonitoring">
      <p class="config-desc">{{ t('telegramMonitor.configDesc') }}</p>
      <div class="input-group">
        <span class="prefix">t.me/</span>
        <input
          v-model="channelName"
          type="text"
          :placeholder="t('telegramMonitor.channelPlaceholder')"
          class="channel-input"
          @keyup.enter="toggleMonitor"
        />
        <button class="btn-primary" @click="toggleMonitor">
          <Play size="14" /> {{ t('common.start') }}
        </button>
      </div>
    </div>

    <!-- Block Content (Active Monitoring) -->
    <div class="block-content" v-else>
      <div class="active-status">
        <div class="status-indicator recording"></div>
        <span class="mono text-muted text-sm flex-1">
          <span v-if="statusMsg" :class="{'text-green': statusMsg.includes('[Connected]'), 'text-red': statusMsg.includes('[Error]')}">
            {{ statusMsg }}
          </span>
          <span v-else>{{ t('telegramMonitor.monitoring') }}: <b class="text-orange">@{{ channelName }}</b></span>
        </span>
        <button class="icon-btn" @click="clearHistory" :title="t('common.delete')">
          <Trash2 size="14" />
        </button>
        <button class="icon-btn stop-btn" @click="toggleMonitor" :title="t('common.stop')">
          <Pause size="14" />
        </button>
      </div>

      <div class="message-feed">
        <div v-for="msg in messages" :key="msg.id" class="tg-message" @mouseenter="handleMouseEnter(channelName, msg)" @mouseleave="handleMouseLeave" @mousemove="handleMouseMove" @click="openMessageLink(channelName, msg.id)">
          <div class="msg-header">
            <span class="msg-author">{{ msg.author }}</span>
            <div class="msg-meta">
              <button v-if="msg.has_media" class="icon-btn media-btn" title="Media Included">
                <ImageIcon size="12" />
              </button>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
          </div>
          <div class="msg-body">{{ msg.text }}</div>
        </div>
      </div>
    </div>

    <!-- Media Hover Overlay -->
    <div v-if="activeMediaUrl" class="media-hover-overlay" :style="{ left: mouseX + 'px', top: (mouseY - 15) + 'px' }">
      <div class="media-hover-content">
        <video v-if="activeMediaType === 'video'" :src="activeMediaUrl" class="media-preview" autoplay loop muted></video>
        <img v-else :src="activeMediaUrl" class="media-preview" alt="Telegram Media" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget-block {
  display: flex;
  flex-direction: column;
  height: 400px;
  min-height: 300px;
  max-height: 800px;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  overflow: hidden;
  resize: vertical;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--overlay-8);
  border-bottom: 1px solid var(--border-color);
}

.block-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-title h3 {
  font-size: 0.95rem;
  font-weight: 500;
  margin: 0;
  color: var(--text-main);
}

.icon-btn {
  color: var(--text-muted);
  transition: var(--transition);
  padding: 4px;

}

.icon-btn:hover {
  color: var(--text-main);
  background: var(--overlay-10);
}

.block-config {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  justify-content: center;
}

.config-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-align: center;
}

.input-group {
  display: flex;
  align-items: center;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  overflow: hidden;
}

.prefix {
  padding: 8px 12px;
  color: var(--text-muted);
  background: var(--overlay-8);
  font-size: 0.9rem;
  border-right: 1px solid var(--border-color);
}

.channel-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  padding: 8px 12px;
  outline: none;
  font-size: 0.9rem;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent-orange);
  border: none;
  border-left: 1px solid var(--border-color);
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: var(--transition);
}

.btn-primary:hover {
  background: rgba(var(--accent-rgb), 0.25);
}

.block-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.active-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(var(--accent-rgb), 0.05);
  border-bottom: 1px solid rgba(var(--accent-rgb), 0.1);
}

.status-indicator {
  width: 8px;
  height: 8px;

  background: var(--accent-orange);
}

.status-indicator.recording {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

.flex-1 {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-sm { font-size: 0.8rem; }
.stop-btn { margin-left: auto; color: var(--accent-red); }

.message-feed {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tg-message {
  background: var(--overlay-8);
  padding: 10px 12px;
  border-left: 3px solid var(--accent-orange);
  cursor: pointer;
  transition: background 0.2s ease;
}

.tg-message:hover {
  background: var(--overlay-10);
}

.msg-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.msg-author {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--accent-orange);
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.media-btn {
  color: var(--accent-orange);
  padding: 2px;
}

.msg-time {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.msg-body {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.4;
}

/* Media Hover Overlay (Mouse Follow) */
.media-hover-overlay {
  position: fixed;
  transform: translate(-50%, -100%);
  z-index: 9999;
  pointer-events: none;
}

.media-hover-content {
  position: relative;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  box-shadow: 0 10px 40px rgba(0,0,0,0.8);
  animation: popIn 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.media-preview {
  max-width: 320px;
  max-height: 320px;
  object-fit: contain;
  border-radius: 4px;
}
</style>
