<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Rss, RefreshCw, Play, Pause, ExternalLink, Upload } from 'lucide-vue-next'

const { t } = useI18n()

const props = defineProps({
  config: Object
})

const emit = defineEmits(['update-config', 'update-data'])

const feedUrl = ref(props.config.url || '')
const isMonitoring = ref(props.config.active !== undefined ? props.config.active : false)
const isFileMode = ref(props.config.isFile || false)
const fileData = ref(props.config.fileData || null)
const fileName = ref(props.config.fileName || '')
const entries = ref([])
const feedTitle = ref('')
const errorMsg = ref('')
const isLoading = ref(false)
let pollInterval = null

function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  fileName.value = file.name
  isFileMode.value = true
  
  const reader = new FileReader()
  reader.onload = async (e) => {
    fileData.value = e.target.result
    emit('update-config', { url: '', active: true, isFile: true, fileName: file.name, fileData: fileData.value })
    isMonitoring.value = true
    await fetchFileFeed(file)
  }
  reader.readAsText(file)
}

async function fetchFileFeed(fileObject = null) {
  isLoading.value = true
  errorMsg.value = ''

  try {
    let formData = new FormData()
    
    if (fileObject) {
      formData.append('file', fileObject)
    } else if (fileData.value) {
      const blob = new Blob([fileData.value], { type: 'text/xml' })
      formData.append('file', blob, fileName.value)
    } else {
      throw new Error("No file data available")
    }

    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/rss/upload`, {
      method: 'POST',
      body: formData
    })
    const data = await res.json()

    if (res.ok && data.status !== 'error') {
      feedTitle.value = data.title
      entries.value = data.entries
      emit('update-data', { type: 'rss', source: fileName.value, title: data.title, items: entries.value })
    } else {
      errorMsg.value = data.message || data.detail || t('rssMonitor.fetchError')
    }
  } catch (e) {
    errorMsg.value = "Failed to parse local file"
  } finally {
    isLoading.value = false
  }
}

async function fetchFeed() {
  if (isFileMode.value) {
    return fetchFileFeed()
  }

  if (!feedUrl.value) return

  isLoading.value = true
  errorMsg.value = ''

  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/rss?url=${encodeURIComponent(feedUrl.value)}`)
    const data = await res.json()

    if (res.ok && data.status !== 'error') {
      feedTitle.value = data.title
      entries.value = data.entries
      emit('update-data', { type: 'rss', source: feedUrl.value, title: data.title, items: entries.value })
    } else {
      errorMsg.value = data.message || data.detail || t('rssMonitor.fetchError')
    }
  } catch (e) {
    errorMsg.value = t('rssMonitor.networkError')
  } finally {
    isLoading.value = false
  }
}

function startPolling() {
  fetchFeed()
  if (!isFileMode.value) {
    pollInterval = setInterval(fetchFeed, 60000)
  }
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function toggleMonitor() {
  if (feedUrl.value.trim() === '') return

  isMonitoring.value = !isMonitoring.value

  if (isMonitoring.value) {
    emit('update-config', { url: feedUrl.value, active: true })
    startPolling()
  } else {
    emit('update-config', { url: feedUrl.value, active: false })
    stopPolling()
  }
}

onMounted(() => {
  if (isMonitoring.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="widget-block glass-panel">
    <!-- Block Header -->
    <div class="block-header">
      <div class="block-title">
        <Rss size="18" class="text-orange" />
        <h3>{{ t('rssMonitor.title') }} <span v-if="feedTitle" class="text-muted text-sm">| {{ feedTitle }}</span></h3>
      </div>
      <div class="block-actions">
        <button class="icon-btn" @click="fetchFeed" :title="t('common.refresh')" v-if="isMonitoring">
          <RefreshCw size="16" :class="{'spin': isLoading}" />
        </button>
      </div>
    </div>

    <!-- Block Config / Input -->
    <div class="block-config" v-if="!isMonitoring">
      <p class="config-desc">{{ t('rssMonitor.configDesc') }}</p>
      <div class="input-group">
          <span class="prefix">URL</span>
        <input
          v-model="feedUrl"
          type="url"
          :placeholder="t('rssMonitor.urlPlaceholder')"
          class="channel-input"
          @keyup.enter="toggleMonitor"
          :disabled="isFileMode"
        />
        <button class="btn-primary" @click="toggleMonitor" :disabled="isFileMode">
          <Play size="14" /> {{ t('common.start') }}
        </button>
      </div>

      <div class="file-upload-section">
        <div class="divider"><span>OR</span></div>
        <input type="file" ref="fileInput" accept=".xml,.rss" style="display: none" @change="handleFileUpload" />
        <button class="btn-secondary" @click="$refs.fileInput.click()">
          <Upload size="14" class="inline" /> Load Local File
        </button>
      </div>
    </div>

    <!-- Block Content (Active Monitoring) -->
    <div class="block-content" v-else>
      <div class="active-status">
        <div class="status-indicator" :class="{'recording': !errorMsg && !isFileMode}"></div>
        <span class="mono text-muted text-sm truncate" style="max-width: 200px;" :title="isFileMode ? fileName : feedUrl">
          {{ errorMsg || (isFileMode ? 'Reading Local File' : t('rssMonitor.activeLabel')) }}
        </span>
        <button class="icon-btn stop-btn" style="margin-left: auto;" @click="toggleMonitor" :title="t('common.stop')">
          <Pause size="14" />
        </button>
      </div>

      <div class="message-feed">
        <div v-for="(entry, idx) in entries" :key="idx" class="rss-entry">
          <div class="msg-header">
            <a :href="entry.link" target="_blank" class="msg-author hover:underline flex gap-1 items-center">
              {{ entry.title }} <ExternalLink size="10" />
            </a>
            <span class="msg-time">{{ entry.published }}</span>
          </div>
          <div class="msg-body">{{ entry.summary }}</div>
        </div>

        <div v-if="entries.length === 0 && !isLoading && !errorMsg" class="p-4 text-center text-muted">
          {{ t('common.noResultsFound') }}
        </div>
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
  white-space: nowrap;
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

.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

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

.file-upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.divider {
  display: flex;
  align-items: center;
  width: 100%;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.divider::before, .divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--border-color);
  margin: 0 12px;
}

.divider span {
  opacity: 0.5;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--overlay-8);
  color: var(--text-main);
  border: 1px dashed var(--border-color);
  padding: 8px 16px;

  font-size: 0.85rem;
  cursor: pointer;
  transition: var(--transition);
}

.btn-secondary:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
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

  background: var(--text-muted);
}

.status-indicator.recording {
  background: var(--accent-orange);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

.text-sm { font-size: 0.8rem; }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stop-btn { margin-left: auto; color: var(--accent-red); }

.message-feed {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rss-entry {
  background: var(--overlay-8);

  padding: 10px 12px;
  border-left: 3px solid var(--accent-green);
}

.msg-header {
  display: flex;
  flex-direction: column;
  margin-bottom: 6px;
  gap: 4px;
}

.msg-author {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent-green);
  text-decoration: none;
}

.hover\:underline:hover {
  text-decoration: underline;
}

.msg-time {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.msg-body {
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.flex { display: flex; }
.gap-1 { gap: 4px; }
.items-center { align-items: center; }
</style>
