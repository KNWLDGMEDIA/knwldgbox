<script setup>
import { ref, onMounted, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { DownloadCloud, Video, Loader2, Youtube, Twitter, Instagram, Settings, Cookie, FileAudio, FolderOpen, RefreshCw, FileVideo, HardDrive } from 'lucide-vue-next'
import { apiService } from '../services/api'
import ConfirmModal from '../components/ui/ConfirmModal.vue'

const tkPath = "M448 209.91a210.06 210.06 0 0 1-122.77-39.25V349.38A162.55 162.55 0 1 1 185 188.31V278.2a74.62 74.62 0 1 0 52.23 71.18V0l88 0a121.18 121.18 0 0 0 1.86 22.17h0A122.18 122.18 0 0 0 381 102.39a121.43 121.43 0 0 0 67 20.14z"

const TikTokIcon = (props) => h('svg', {
  xmlns: 'http://www.w3.org/2000/svg',
  width: props.size || 24,
  height: props.size || 24,
  viewBox: '-20 -20 488 552',
  class: props.class
}, [
  h('path', { d: tkPath, fill: '#25F4EE', transform: 'translate(-12, -12)' }),
  h('path', { d: tkPath, fill: '#FE2C55', transform: 'translate(12, 12)' }),
  h('path', { d: tkPath, fill: '#FFFFFF' })
])

const { t } = useI18n()

const url = ref('')
const isDownloading = ref(false)
const progressMessages = ref([])
const ws = ref(null)
const showAdvanced = ref(false)
const selectedCookie = ref('none')
const selectedFormat = ref('best')
const libraryFiles = ref([])
const isFetchingLibrary = ref(false)

const showErrorModal = ref(false)
const errorTitle = ref('')
const errorMessage = ref('')

const platformInfo = [
  { name: 'TikTok', icon: TikTokIcon, color: 'text-white' },
  { name: 'YouTube', icon: Youtube, color: 'text-red' },
  { name: 'Twitter / X', icon: Twitter, color: 'text-blue' },
  { name: 'Instagram', icon: Instagram, color: 'text-purple' }
]

function startDownload() {
  if (!url.value.trim() || isDownloading.value) return

  isDownloading.value = true
  progressMessages.value = []
  let terminalMessageReceived = false

  ws.value = apiService.createDownloaderWebSocket()

  ws.value.onopen = () => {
    ws.value.send(JSON.stringify({
      action: 'download',
      url: url.value,
      cookies: selectedCookie.value,
      format: selectedFormat.value
    }))
  }

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    progressMessages.value.push(data)

    if (data.type === 'done' || data.type === 'error') {
      terminalMessageReceived = true
      isDownloading.value = false
      ws.value.close()
    }
  }

  ws.value.onerror = () => {
    progressMessages.value.push({ type: 'error', text: 'WebSocket connection failed.' })
    isDownloading.value = false
  }

  ws.value.onclose = () => {
    if (!terminalMessageReceived && isDownloading.value) {
      progressMessages.value.push({ type: 'error', text: 'Download connection closed unexpectedly.' })
      isDownloading.value = false
    }
    ws.value = null
  }
}

function stopDownload() {
  if (ws.value) {
    ws.value.close()
  }
  isDownloading.value = false
  progressMessages.value.push({ type: 'error', text: 'Download aborted by user.' })
}

async function fetchLibrary() {
  isFetchingLibrary.value = true
  try {
    const data = await apiService.listDownloads()
    if (data.status === 'success') {
      libraryFiles.value = data.data
    }
  } catch (err) {
    console.error("Failed to fetch library:", err)
  } finally {
    isFetchingLibrary.value = false
  }
}

async function openDirectory() {
  try {
    const res = await apiService.openDownloadsDirectory()
    if (res && res.status === 'error') {
      if (res.message.includes('container') || res.message.includes('host machine')) {
        errorTitle.value = t('mediaDownloaders.dockerErrorTitle')
        errorMessage.value = t('mediaDownloaders.dockerErrorMessage')
      } else {
        errorTitle.value = 'Error'
        errorMessage.value = res.message
      }
      showErrorModal.value = true
    }
  } catch (err) {
    console.error("Failed to open directory:", err)
    errorTitle.value = 'Error'
    errorMessage.value = t('mediaDownloaders.openDirError', 'Failed to open directory. See console for details.')
    showErrorModal.value = true
  }
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function downloadFileToPc(filename) {
  const url = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/downloads/file/${encodeURIComponent(filename)}`
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

onMounted(() => {
  fetchLibrary()
})
</script>

<template>
  <div class="downloaders-view">
    <header class="page-header">
      <div>
        <h1><DownloadCloud class="icon-title" /> {{ t('mediaDownloaders.title') }}</h1>
        <p class="subtitle">{{ t('mediaDownloaders.subtitle') }}</p>
      </div>
    </header>

    <div class="platforms-banner">
      <div v-for="p in platformInfo" :key="p.name" class="platform-card glass-panel">
        <component :is="p.icon" size="24" :class="p.color" />
        <span>{{ p.name }}</span>
      </div>
    </div>

    <div class="downloader-panel glass-panel">
      <div class="input-wrapper">
        <Video class="icon-input" size="20" />
        <input
          v-model="url"
          type="text"
          :placeholder="t('mediaDownloaders.urlPlaceholder')"
          @keyup.enter="startDownload"
          :disabled="isDownloading"
        />
        <button class="btn-settings" @click="showAdvanced = !showAdvanced" :class="{ active: showAdvanced }">
          <Settings size="18" />
        </button>
        <button class="btn-download" @click="startDownload" v-if="!isDownloading">
          <DownloadCloud size="18" /> {{ t('mediaDownloaders.download') }}
        </button>
        <button class="btn-stop" @click="stopDownload" v-else>
          <Loader2 size="18" class="spin" /> {{ t('mediaDownloaders.cancel') }}
        </button>
      </div>

      <!-- Settings Panel -->
      <div class="settings-panel" v-if="showAdvanced">
        <div class="setting-item">
          <div class="setting-header">
            <Cookie size="16" class="text-orange" />
            <label>{{ t('mediaDownloaders.useBrowserCookies') }}</label>
            <select v-model="selectedCookie" class="custom-select" :disabled="isDownloading">
              <option value="none">{{ t('mediaDownloaders.noCookie') }}</option>
              <option value="chrome">Chrome</option>
              <option value="firefox">Firefox</option>
              <option value="brave">Brave</option>
              <option value="edge">Edge</option>
              <option value="opera">Opera</option>
              <option value="vivaldi">Vivaldi</option>
              <option value="safari">Safari</option>
            </select>
          </div>
          <p class="setting-desc">{{ t('mediaDownloaders.cookieHelp') }}</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <FileAudio size="16" class="text-blue" />
            <label>{{ t('mediaDownloaders.downloadFormat') }}</label>
            <select v-model="selectedFormat" class="custom-select" :disabled="isDownloading">
              <option value="best">{{ t('mediaDownloaders.bestVideoAudio') }}</option>
              <option value="audio">{{ t('mediaDownloaders.audioOnly') }}</option>
            </select>
          </div>
          <p class="setting-desc">{{ t('mediaDownloaders.formatHelp') }}</p>
        </div>
      </div>

      <div class="progress-box" v-if="progressMessages.length > 0">
        <div
          v-for="(msg, i) in progressMessages"
          :key="i"
          class="log-line"
          :class="msg.type"
        >
          {{ msg.text }}
        </div>
      </div>
    </div>

    <!-- Media Library Panel -->
    <div class="library-panel glass-panel">
      <div class="library-header">
        <div class="library-title">
          <HardDrive size="20" class="text-green" />
          <h2>{{ t('mediaDownloaders.libraryTitle') }}</h2>
        </div>
        <div class="library-actions">
          <button class="btn-action" @click="fetchLibrary" :disabled="isFetchingLibrary">
            <RefreshCw size="16" :class="{ 'spin': isFetchingLibrary }" /> {{ t('mediaDownloaders.refresh') }}
          </button>
          <button class="btn-action primary" @click="openDirectory">
            <FolderOpen size="16" /> {{ t('mediaDownloaders.openDirectory') }}
          </button>
        </div>
      </div>

      <div class="library-content">
        <div v-if="libraryFiles.length === 0" class="empty-library">
          <FileVideo size="32" class="empty-icon" />
          <p>{{ t('mediaDownloaders.emptyLibrary') }}</p>
        </div>

        <div v-else class="media-list">
          <div v-for="file in libraryFiles" :key="file.name" class="media-item glass-panel">
            <div class="media-icon">
              <FileAudio v-if="file.name.endsWith('.mp3')" size="24" class="text-blue" />
              <FileVideo v-else size="24" class="text-orange" />
            </div>
            <div class="media-details">
              <div class="media-name mono" :title="file.name">{{ file.name }}</div>
              <div class="media-meta">
                <span class="media-size">{{ formatSize(file.size) }}</span>
                <span class="media-dot">•</span>
                <span class="media-date">{{ new Date(file.time * 1000).toLocaleString() }}</span>
              </div>
            </div>
            <button class="btn-download-sm" @click="downloadFileToPc(file.name)" :title="t('mediaDownloaders.downloadToPc')">
              <DownloadCloud size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Modal -->
    <ConfirmModal
      :show="showErrorModal"
      :title="errorTitle"
      :message="errorMessage"
      :isDestructive="false"
      confirmText="OK"
      @cancel="showErrorModal = false"
      @confirm="showErrorModal = false"
    />
  </div>
</template>

<style scoped>
.downloaders-view {
  padding: 32px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 2rem;
  color: var(--text-main);
  margin-bottom: 8px;
}

.icon-title {
  color: var(--accent-orange);
}

.subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

.platforms-banner {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.platform-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  background: var(--overlay-8);
}

.text-white { color: #fff; }
.text-red { color: #ff0000; }
.text-blue { color: #1da1f2; }
.text-purple { color: #c13584; }

.downloader-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  padding: 4px;
  transition: var(--transition);
}
.input-wrapper:focus-within {
  border-color: var(--border-highlight);

}

.icon-input {
  position: absolute;
  left: 16px;
  color: var(--text-muted);
}

.input-wrapper input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  padding: 12px 16px 12px 48px;
  font-size: 1rem;
  outline: none;
}
.input-wrapper input::placeholder {
  color: var(--text-muted);
}

.btn-download {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--accent-orange);
  color: #fff;
  border: none;
  padding: 10px 20px;

  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}
.btn-download:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);

}

.btn-stop {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--overlay-8);
  color: var(--accent-red);
  border: 1px solid var(--accent-red);
  padding: 10px 20px;

  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}
.btn-stop:hover {
  background: var(--overlay-10);
}

.btn-settings {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  padding: 10px 12px;

  cursor: pointer;
  transition: var(--transition);
  margin-right: 8px;
}
.btn-settings:hover, .btn-settings.active {
  background: var(--overlay-10);
  color: var(--text-main);
}

/* ── Settings Panel ───────────────────────────── */
.settings-panel {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-header {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-main);
  font-size: 0.9rem;
  font-weight: 500;
}
.setting-header label { flex: 1; margin-bottom: 0; }

.setting-desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  padding-left: 28px;
  margin: 0;
}

.custom-select {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-main);

  padding: 6px 12px;
  font-family: inherit;
  font-size: 0.9rem;
  outline: none;
  cursor: pointer;
}
.custom-select:focus {
  border-color: var(--accent-orange);
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.progress-box {
  background: var(--bg-dark);

  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-line { color: var(--text-muted); }
.log-line.info { color: var(--accent-blue); }
.log-line.progress { color: var(--accent-orange); }
.log-line.done { color: var(--accent-green); font-weight: bold; }
.log-line.error { color: var(--accent-red); font-weight: bold; }

::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-thumb {
  background: var(--border-color);

}

/* ── Library Panel ───────────────────────────── */
.library-panel {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 16px;
}

.library-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.library-title h2 {
  font-size: 1.2rem;
  margin: 0;
  color: var(--text-main);
}
.text-green { color: var(--accent-green); }

.library-actions {
  display: flex;
  gap: 12px;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--overlay-8);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  padding: 8px 16px;

  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
}
.btn-action:hover:not(:disabled) {
  background: var(--overlay-10);
  color: var(--text-main);
}
.btn-action.primary {
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--accent-orange);
  border-color: rgba(var(--accent-rgb), 0.3);
}
.btn-action.primary:hover {
  background: rgba(var(--accent-rgb), 0.2);
}

.library-content {
  overflow: hidden;
}

.empty-library {
  padding: 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-muted);
  background: var(--overlay-8);

  border: 1px solid var(--border-color);
}
.empty-icon {
  opacity: 0.5;
}

.media-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.media-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  cursor: default;
  transition: var(--transition);
  border: 1px solid var(--overlay-8);
}

.media-item:hover {
  background: var(--overlay-10);
  border-color: rgba(var(--accent-rgb), 0.3);
  transform: translateY(-2px);
}

.media-icon {
  width: 48px;
  height: 48px;

  background: var(--bg-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--overlay-8);
}

.media-details {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 6px;
}

.media-name {
  color: var(--text-main);
  font-size: 0.95rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.media-dot {
  opacity: 0.5;
}

.media-size {
  color: var(--accent-green);
  font-family: 'JetBrains Mono', monospace;
}

.btn-download-sm {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--accent-orange);
  border: 1px solid rgba(var(--accent-rgb), 0.3);

  cursor: pointer;
  transition: all 0.2s;
}

.btn-download-sm:hover {
  background: rgba(var(--accent-rgb), 0.2);
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .platforms-banner {
    flex-wrap: wrap;
  }
  .platform-card {
    min-width: calc(50% - 8px);
  }
  .input-wrapper {
    flex-wrap: wrap;
    padding: 8px;
    gap: 8px;
    background: transparent;
    border: none;
  }
  .input-wrapper input {
    width: 100%;
    padding-left: 40px;
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
  }
  .icon-input {
    top: 20px;
  }
  .btn-settings, .btn-download, .btn-stop {
    flex: 1;
    margin: 0;
  }
  .library-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .library-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  .btn-action {
    flex: 1;
    justify-content: center;
  }
}
</style>
