<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { FileArchive, FileImage, FileText, Download, ExternalLink, RefreshCw, Trash2 } from 'lucide-vue-next'
import ConfirmModal from '../components/ui/ConfirmModal.vue'

const { t } = useI18n()

const archives = ref([])
const isLoading = ref(false)

const urlToArchive = ref('')
const isArchiving = ref(false)
const errorMsg = ref(null)

const showDeleteModal = ref(false)
const archiveToDelete = ref(null)

const hoverImg = ref(null)
const mouseX = ref(0)
const mouseY = ref(0)

function onMouseMove(e) {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

function showPreview(file) {
  if (file) hoverImg.value = `${ASSET_BASE}/${file}`
}

function hidePreview() {
  hoverImg.value = null
}

const API_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api`
const ASSET_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/archives`

async function fetchArchives() {
  isLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/archives`)
    archives.value = await res.json()
  } catch (e) {
    console.error("Failed to load archives", e)
  } finally {
    isLoading.value = false
  }
}

async function archiveTarget() {
  if (!urlToArchive.value.trim()) return

  isArchiving.value = true
  errorMsg.value = null

  try {
    let url = urlToArchive.value.trim()
    if (!url.startsWith('http')) url = `https://${url}`

    const res = await fetch(`${API_BASE}/archive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })

    if (res.ok) {
      urlToArchive.value = ''
      await fetchArchives()
    } else {
      const errorData = await res.json()
      errorMsg.value = `${t('archives.archiveFailed')} ${errorData.detail || 'Unknown error'}`
    }
  } catch (err) {
    errorMsg.value = `${t('archives.archiveFailed')} ${err.message}`
  } finally {
    isArchiving.value = false
  }
}

function confirmDeleteArchive(archiveId) {
  archiveToDelete.value = archiveId
  showDeleteModal.value = true
}

async function deleteArchive() {
  if (!archiveToDelete.value) return

  const archiveId = archiveToDelete.value
  showDeleteModal.value = false
  archiveToDelete.value = null

  try {
    const res = await fetch(`${API_BASE}/archives/${archiveId}`, {
      method: 'DELETE'
    })
    if (res.ok) {
      await fetchArchives()
    }
  } catch (err) {
    console.error("Failed to delete archive", err)
  }
}

function openFile(filename) {
  if (filename) {
    window.open(`${ASSET_BASE}/${filename}`, '_blank')
  }
}

onMounted(() => {
  fetchArchives()
})
</script>

<template>
  <div class="archives-page">
    <div class="header-section">
      <h1 class="page-title">{{ t('archives.title') }}</h1>
      <p class="page-subtitle">{{ t('archives.subtitle') }}</p>

      <div class="archive-controls">
        <div class="archive-input-wrapper">
          <input
            type="text"
            v-model="urlToArchive"
            :placeholder="t('archives.urlPlaceholder')"
            class="url-input"
            @keyup.enter="archiveTarget"
            :disabled="isArchiving"
          />
          <button class="btn-primary archive-btn" @click="archiveTarget" :disabled="isArchiving || !urlToArchive.trim()">
            <FileArchive size="16" />
            <span>{{ isArchiving ? t('archives.archiving') : t('archives.archiveUrl') }}</span>
          </button>
        </div>
        <button class="btn-refresh" @click="fetchArchives" :disabled="isLoading">
          <RefreshCw size="16" :class="{ 'spin': isLoading }" />
          {{ t('archives.refresh') }}
        </button>
      </div>

      <div v-if="errorMsg" class="error-text">{{ errorMsg }}</div>
    </div>

    <div class="archives-grid">
      <div v-for="arc in archives" :key="arc.archive_id" class="archive-card glass-panel">
        <div class="card-header">
          <FileArchive size="24" class="text-orange" />
          <h3 class="truncate" :title="arc.archive_id">{{ arc.archive_id }}</h3>
          <button class="delete-btn" @click="confirmDeleteArchive(arc.archive_id)" title="Delete Archive">
            <Trash2 size="16" />
          </button>
        </div>

        <div class="card-actions">
          <button
            class="action-btn"
            :disabled="!arc.png_file"
            @click="openFile(arc.png_file)"
            @mouseenter="showPreview(arc.png_file)"
            @mouseleave="hidePreview"
            @mousemove="onMouseMove"
          >
            <FileImage size="18" />
            <span>{{ t('archives.screenshot') }}</span>
            <ExternalLink size="14" class="icon-right" />
          </button>

          <button
            class="action-btn"
            :disabled="!arc.pdf_file"
            @click="openFile(arc.pdf_file)"
          >
            <FileText size="18" />
            <span>{{ t('archives.pdfPrint') }}</span>
            <Download size="14" class="icon-right" />
          </button>
        </div>
      </div>

      <div v-if="archives.length === 0 && !isLoading" class="empty-state glass-panel">
        <FileArchive size="48" class="empty-icon" />
        <h3>{{ t('archives.noArchivesFound') }}</h3>
        <p>{{ t('archives.noArchivesMessage') }}</p>
      </div>
    </div>

    <ConfirmModal
      :show="showDeleteModal"
      :title="t('archives.deleteArchiveTitle')"
      :message="t('archives.deleteArchiveMessage')"
      :confirmText="t('archives.delete')"
      :cancelText="t('archives.cancel')"
      :isDestructive="true"
      @confirm="deleteArchive"
      @cancel="showDeleteModal = false; archiveToDelete = null"
    />

    <!-- Floating Image Preview -->
    <div
      v-if="hoverImg"
      class="floating-preview"
      :style="{ top: mouseY + 15 + 'px', left: mouseX + 15 + 'px' }"
    >
      <img :src="hoverImg" alt="Preview" />
    </div>
  </div>
</template>

<style scoped>
.archives-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
}

.header-section {
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.page-title { font-size: 2rem; margin: 0; }
.page-subtitle { color: var(--text-muted); font-size: 0.95rem; margin-bottom: 8px; }

.archive-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  margin-top: 8px;
}

.archive-input-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 600px;
  background: var(--bg-panel);
  padding: 6px 6px 6px 16px;

  border: 1px solid var(--border-color);
}

.url-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 0.95rem;
  outline: none;
}
.url-input::placeholder { color: var(--text-muted); }

.archive-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--accent-orange);
  color: #000;
  border: none;

  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.archive-btn:hover:not(:disabled) {
  filter: brightness(1.15);
}
.archive-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error-text {
  color: var(--accent-red);
  font-size: 0.85rem;
  margin-top: 4px;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 8px 16px;

  cursor: pointer;
  transition: all 0.2s;
}
.btn-refresh:hover:not(:disabled) {
  background: var(--overlay-10);
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.archives-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.archive-card {
  padding: 20px;

  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.card-header h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  flex: 1;
}
.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;

  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.delete-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-red);
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 12px;

  cursor: pointer;
  transition: all 0.2s;
}
.action-btn:hover:not(:disabled) {
  background: rgba(var(--accent-rgb), 0.1);
  border-color: rgba(var(--accent-rgb), 0.3);
  color: var(--accent-orange);
}
.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.icon-right { margin-left: auto; opacity: 0.5; }
.action-btn:hover:not(:disabled) .icon-right { opacity: 1; }

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  text-align: center;

}
.empty-icon { color: var(--text-muted); margin-bottom: 16px; opacity: 0.5; }
.text-orange { color: var(--accent-orange); }

/* Floating Preview */
.floating-preview {
  position: fixed;
  z-index: 10000;
  pointer-events: none;
  background: var(--bg-panel);
  padding: 6px;

  border: 1px solid var(--border-color);

  width: 300px;
  animation: fade-in 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fade-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.floating-preview img {
  width: 100%;
  height: 350px;
  object-fit: cover;
  object-position: top;

  display: block;
}
</style>
