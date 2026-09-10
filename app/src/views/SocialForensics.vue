<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { User, Hash, Globe, FileJson, Mail, DownloadCloud, Activity } from 'lucide-vue-next'
import SherlockModule from '../components/social/SherlockModule.vue'
import TiktokModule from '../components/social/TiktokModule.vue'
import GHuntModule from '../components/social/GHuntModule.vue'
import MaigretModule from '../components/social/MaigretModule.vue'
import HoleheModule from '../components/social/HoleheModule.vue'
import html2pdf from 'html2pdf.js'

import { useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()

const activeTab = ref(route.query.tab || 'sherlock')

watch(() => route.query.tab, (newTab) => {
  if (newTab) activeTab.value = newTab
})

const isExporting = ref(false)

async function exportToPdf() {
  if (isExporting.value) return
  isExporting.value = true

  // Find the currently active tab content
  const activeTabs = document.querySelectorAll('.tab-content')
  let element = null
  for (const tab of activeTabs) {
    if (tab.style.display !== 'none') {
      element = tab
      break
    }
  }

  if (!element) {
    isExporting.value = false
    return
  }

  const opt = {
    margin:       10,
    filename:     `${activeTab.value}-social-forensics.pdf`,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true, backgroundColor: document.body.classList.contains('light-mode') ? '#F3F4F6' : '#07090E' },
    jsPDF:        { unit: 'mm', format: 'a3', orientation: 'portrait' }
  }

  try {
    await html2pdf().set(opt).from(element).save()
  } catch (err) {
    console.error("PDF Export failed:", err)
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <div class="forensics-page">
    <div class="header-section">
      <div>
        <h1 class="page-title">{{ t('socialForensics.title') }}</h1>
        <p class="page-subtitle">{{ t('socialForensics.subtitle') }}</p>
      </div>
      <button class="export-btn" @click="exportToPdf" :disabled="isExporting">
        <component :is="isExporting ? Activity : DownloadCloud" size="16" />
        {{ isExporting ? t('socialForensics.generatingPdf') : t('socialForensics.exportPdf') }}
      </button>
    </div>

    <!-- Tabs -->
    <div class="tabs-container">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'sherlock' }"
        @click="activeTab = 'sherlock'"
      >
          <User size="18" /> {{ t('socialForensics.sherlockTab') }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'ghunt' }"
        @click="activeTab = 'ghunt'"
      >
        <Globe size="18" /> {{ t('socialForensics.ghuntTab') }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'holehe' }"
        @click="activeTab = 'holehe'"
      >
        <Mail size="18" /> {{ t('socialForensics.holeheTab') }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'maigret' }"
        @click="activeTab = 'maigret'"
      >
        <FileJson size="18" /> {{ t('socialForensics.maigretTab') }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'tiktok' }"
        @click="activeTab = 'tiktok'"
      >
        <Hash size="18" /> {{ t('socialForensics.tiktokTab') }}
      </button>
    </div>

    <div v-show="activeTab === 'sherlock'" class="tab-content">
      <SherlockModule />
    </div>

    <div v-show="activeTab === 'ghunt'" class="tab-content">
      <GHuntModule />
    </div>

    <div v-show="activeTab === 'holehe'" class="tab-content">
      <HoleheModule />
    </div>

    <div v-show="activeTab === 'maigret'" class="tab-content">
      <MaigretModule />
    </div>

    <div v-show="activeTab === 'tiktok'" class="tab-content">
      <TiktokModule />
    </div>
  </div>
</template>

<style scoped>
.forensics-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding-right: 8px;
}

.header-section {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.page-title { font-size: 2rem; margin-bottom: 8px; }
.page-subtitle { color: var(--text-muted); font-size: 0.95rem; }

.export-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent-orange);
  border: 1px solid rgba(var(--accent-rgb), 0.3);
  padding: 10px 16px;

  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}

.export-btn:hover:not(:disabled) {
  background: rgba(var(--accent-rgb), 0.25);
  transform: translateY(-2px);
}

.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tabs-container {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;

  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  transition: var(--transition);
}

.tab-btn:hover {
  background: var(--overlay-light-5);
  color: var(--text-main);
}

.tab-btn.active {
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--accent-orange);
  border: 1px solid rgba(var(--accent-rgb), 0.3);
}

.tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
}

@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    gap: 12px;
  }
  .export-btn {
    width: 100%;
    justify-content: center;
  }
  .tabs-container {
    flex-wrap: wrap;
    gap: 8px;
    border-bottom: none;
  }
  .tab-btn {
    flex: 1;
    min-width: calc(33% - 8px);
    justify-content: center;
    padding: 8px;
    font-size: 0.8rem;
  }
}
</style>
