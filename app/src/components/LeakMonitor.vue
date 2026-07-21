<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ExternalLink, RefreshCw, AlertTriangle, Play, Pause, Database } from 'lucide-vue-next'

const { t } = useI18n()

const props = defineProps({
  config: { type: Object, required: true }
})



const isMonitoring = ref(props.config.active !== undefined ? props.config.active : false)
const leaks = ref([])
const errorMsg = ref('')
const isLoading = ref(false)
const lastUpdate = ref('')

let pollInterval = null

// Load from cache initially
onMounted(() => {
  const saved = localStorage.getItem('knwldg_fb_leaks')
  if (saved) {
    try {
      leaks.value = JSON.parse(saved)
    } catch (e) {}
  }

  if (isMonitoring.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

async function fetchLeaks() {
  isLoading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/dataleaks/frenchbreaches`)
    const data = await res.json()
    if (data.status === 'success') {
      leaks.value = data.data
      localStorage.setItem('knwldg_fb_leaks', JSON.stringify(leaks.value))

      const now = new Date()
      lastUpdate.value = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
    } else {
      errorMsg.value = data.error || t('leakMonitor.fetchError')
    }
  } catch (err) {
    errorMsg.value = t('leakMonitor.apiError')
  } finally {
    isLoading.value = false
  }
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval)
  fetchLeaks()
  pollInterval = setInterval(fetchLeaks, 15 * 60 * 1000) // Poll every 15 minutes
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function toggleMonitor() {
  isMonitoring.value = !isMonitoring.value
  if (isMonitoring.value) {
    startPolling()
  } else {
    stopPolling()
  }
}



function formatDesc(text) {
  if (!text) return ''
  // Convert URLs to clickable links
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.replace(urlRegex, '<a href="$1" target="_blank" class="leak-inline-link">$1</a>')
}
</script>

<template>
  <div class="monitor-block" :style="{ height: config.height ? `${config.height}px` : '400px' }">
    <div class="block-header glass-panel">
      <div class="header-left">
        <div class="icon-box" style="background: rgba(239, 68, 68, 0.1); color: #EF4444;">
          <Database size="16" />
        </div>
        <h3 class="block-title">{{ t('leakMonitor.title') }}</h3>
      </div>
      <div class="header-right">
        <button class="icon-btn" @click="fetchLeaks" :title="t('common.refresh')" :class="{'spinning': isLoading}" v-if="isMonitoring">
          <RefreshCw size="14" />
        </button>
      </div>
    </div>

    <!-- Block Config / Input -->
    <div class="block-config" v-if="!isMonitoring">
      <p class="config-desc">{{ t('leakMonitor.configDesc') }}</p>
      <button class="btn-primary" @click="toggleMonitor">
        <Play size="14" /> {{ t('leakMonitor.startMonitoring') }}
      </button>
    </div>

    <!-- Block Content (Active Monitoring) -->
    <div class="block-content" v-else>
      <div class="active-status">
        <div class="status-indicator recording"></div>
        <span class="mono text-muted text-sm flex-1">
          <span v-if="errorMsg" class="text-red">{{ errorMsg }}</span>
          <span v-else>{{ t('leakMonitor.polling') }} <span v-if="lastUpdate">({{ t('leakMonitor.lastUpdate') }}: {{ lastUpdate }})</span></span>
        </span>
        <button class="icon-btn stop-btn" @click="toggleMonitor" :title="t('common.stop')">
          <Pause size="14" />
        </button>
      </div>

      <div class="messages-container custom-scrollbar">
        <div v-if="leaks.length === 0 && !isLoading && !errorMsg" class="empty-state">
          {{ t('leakMonitor.noLeaksFound') }}
        </div>

        <div class="leak-item" v-for="leak in leaks" :key="leak.id">
          <div class="leak-header">
            <h4 class="leak-title">
              <AlertTriangle size="14" class="text-red" />
              {{ leak.title }}
            </h4>
            <span class="leak-date">{{ leak.date }}</span>
          </div>

          <p class="leak-desc" v-html="formatDesc(leak.description)"></p>

          <div class="leak-meta" v-if="leak.impact || leak.tags.length > 0">
            <span class="impact-badge" v-if="leak.impact">{{ leak.impact }}</span>
            <div class="leak-tags">
              <span class="leak-tag" v-for="tag in leak.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>

          <a :href="leak.url" target="_blank" class="leak-link">
            <ExternalLink size="12" /> {{ t('leakMonitor.source') }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitor-block {
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  overflow: hidden;
  resize: vertical;
  min-height: 250px;
  position: relative;
  transition: border-color 0.2s ease;
}

.monitor-block:focus-within {
  border-color: rgba(239, 68, 68, 0.4);
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--overlay-bg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-box {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;

}

.block-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-main);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: var(--transition);
  padding: 4px;

}

.icon-btn:hover {
  color: var(--text-main);
  background: var(--overlay-10);
}
.close-btn:hover {
  color: var(--accent-red);
  background: rgba(239, 68, 68, 0.1);
}

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.block-config {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  justify-content: center;
  align-items: center;
}

.config-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-align: center;
  max-width: 80%;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 8px 16px;

  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: var(--transition);
}

.btn-primary:hover {
  background: rgba(239, 68, 68, 0.25);
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
  background: rgba(239, 68, 68, 0.05);
  border-bottom: 1px solid rgba(239, 68, 68, 0.1);
}

.status-indicator {
  width: 8px;
  height: 8px;

  background: var(--accent-red);
}
.status-indicator.recording { animation: pulse-red 1.5s infinite; }

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.leak-item {
  background: var(--overlay-20);
  border: 1px solid var(--border-color);

  padding: 12px;
  transition: transform 0.2s ease, border-color 0.2s ease;
}
.leak-item:hover {
  border-color: rgba(239, 68, 68, 0.4);
}

.leak-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 16px;
}

.leak-title {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
  flex: 1;
  word-break: break-word;
}

.leak-date {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.leak-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0 0 12px 0;
}

.leak-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.impact-badge {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  padding: 2px 6px;

  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.leak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.leak-tag {
  background: var(--overlay-5);
  color: var(--text-muted);
  padding: 2px 6px;

  font-size: 0.7rem;
  border: 1px solid var(--border-color);
}

.leak-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--accent-blue);
  text-decoration: none;
  transition: color 0.2s ease;
}
.leak-link:hover {
  color: #60A5FA;
}

:deep(.leak-inline-link) {
  color: var(--accent-blue);
  text-decoration: underline;
}
:deep(.leak-inline-link:hover) {
  color: #60A5FA;
}

.empty-state {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
  padding: 32px 0;
}

.flex-1 { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-sm { font-size: 0.8rem; }
.text-red {   color: var(--accent-red) !important; }
.text-muted { color: var(--text-muted); }
.mono { font-family: 'JetBrains Mono', monospace; }

@media (max-width: 768px) {
  .leak-header {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
