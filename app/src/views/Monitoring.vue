<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import draggable from 'vuedraggable'
import { Plus, X, MessageCircle, Rss, LayoutGrid, List as ListIcon, Search, Upload, Edit2, Sparkles, ChevronUp, ChevronDown } from 'lucide-vue-next'
import { marked } from 'marked'
import TelegramMonitor from '../components/TelegramMonitor.vue'
import RssMonitor from '../components/RssMonitor.vue'
import MonitoringMap from '../components/MonitoringMap.vue'
import { globalMapLocations } from '../store.js'

const { t, locale } = useI18n()

const STORAGE_KEY = 'knwldg_monitoring_blocks'

const activeBlocks = ref([])

onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && saved !== '[]') {
    try {
      activeBlocks.value = JSON.parse(saved)
    } catch (e) {
      activeBlocks.value = [{ id: '1', type: 'telegram_monitor', config: { channel: '' } }]
    }
  } else {
    activeBlocks.value = [{ id: '1', type: 'telegram_monitor', config: { channel: '' } }]
  }
})

// Watch for deep changes in blocks (reordering or config changes)
watch(activeBlocks, (newVal) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
}, { deep: true })

const isAddingBlock = ref(false)
const isAddingFeedSource = ref(false)
const viewMode = ref(localStorage.getItem('knwldg_monitoring_view') || 'grid')

watch(viewMode, (newVal) => {
  localStorage.setItem('knwldg_monitoring_view', newVal)
})

const feedData = ref({})
const feedSearch = ref('')
const isSummarizing = ref(false)
const aiSummary = ref(null)
const aiSummaryHidden = ref(false)

const mapLocations = globalMapLocations
const processedItemIds = new Set()

async function summarizeToday() {
  if (filteredFeed.value.length === 0) return
  isSummarizing.value = true
  aiSummary.value = null
  aiSummaryHidden.value = false

  try {
    const recentEntries = filteredFeed.value.slice(0, 20).map(item => ({
      title: item.author,
      summary: item.text,
      link: item.link,
      time: item.time
    }))

    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/rss/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries: recentEntries, language: locale.value })
    })

    const data = await res.json()
    if (res.ok && data.status === 'success') {
      aiSummary.value = marked(data.summary)
    } else {
      console.error('Failed to summarize via OpenRouter', data)
    }
  } catch (err) {
    console.error("Failed to reach AI endpoint.", err)
  } finally {
    isSummarizing.value = false
  }
}

function handleFeedData(id, data) {
  feedData.value[id] = data
}

function parseTime(timeStr) {
  if (!timeStr) return 0
  const ts = Date.parse(timeStr)
  if (!isNaN(ts)) return ts

  const now = new Date()
  const parts = timeStr.split(':')
  if (parts.length >= 2) {
    now.setHours(parseInt(parts[0], 10))
    now.setMinutes(parseInt(parts[1], 10))
    now.setSeconds(0)
    return now.getTime()
  }
  return 0
}

const aggregatedFeed = computed(() => {
  let allItems = []
  for (const id in feedData.value) {
    const data = feedData.value[id]
    if (!data || !data.items) continue
    
    const block = activeBlocks.value.find(b => b.id === id)
    const customName = block && block.config.customName ? block.config.customName : null
    
    if (data.type === 'telegram') {
      const sourceName = customName || ('@' + data.source)
      data.items.forEach(msg => {
        allItems.push({
          id: msg.id || Math.random().toString(),
          sourceType: 'telegram',
          sourceName: sourceName,
          author: msg.author,
          timestamp: parseTime(msg.time),
          timeStr: msg.time,
          text: msg.text,
          link: `https://t.me/${data.source}/${msg.id}`,
          hasMedia: msg.has_media,
          mediaType: msg.media_type
        })
      })
    } else if (data.type === 'rss') {
      let siteName = customName
      if (!siteName) {
        siteName = data.source
        if (siteName && siteName.startsWith('http')) {
          try {
            siteName = new URL(siteName).hostname.replace('www.', '')
          } catch(e) {
            siteName = data.title || data.source
          }
        } else {
          siteName = data.source // e.g. local filename
        }
      }
      
      data.items.forEach(entry => {
        allItems.push({
          id: entry.link || Math.random().toString(),
          sourceType: 'rss',
          sourceName: siteName,
          author: entry.title,
          link: entry.link,
          timestamp: parseTime(entry.published),
          timeStr: entry.published,
          text: entry.summary,
          media: entry.media || null
        })
      })
    }
  }
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  return allItems
    .filter(item => item.timestamp >= today.getTime())
    .sort((a, b) => b.timestamp - a.timestamp)
})

const filteredFeed = computed(() => {
  if (!feedSearch.value) return aggregatedFeed.value
  const lowerSearch = feedSearch.value.toLowerCase()
  return aggregatedFeed.value.filter(item => 
    (item.text && item.text.toLowerCase().includes(lowerSearch)) ||
    (item.author && item.author.toLowerCase().includes(lowerSearch)) ||
    (item.sourceName && item.sourceName.toLowerCase().includes(lowerSearch))
  )
})

watch(aggregatedFeed, async (newFeed) => {
  const newItems = newFeed.filter(item => !processedItemIds.has(item.id))
  
  if (newItems.length === 0) return
  
  for (const item of newItems) {
    processedItemIds.add(item.id)
    
    const fullText = (item.author || '') + " " + (item.text || '')
    if (fullText.length < 10) continue
    
    try {
      const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/extract_locations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: fullText })
      })
      
      const data = await res.json()
      if (data.status === 'success' && data.locations) {
        const currentLocations = [...mapLocations.value]
        
        data.locations.forEach(loc => {
          if (!currentLocations.some(m => m.name === loc.name)) {
            currentLocations.push({
              name: loc.name,
              lat: loc.lat,
              lng: loc.lng,
              title: item.sourceType === 'rss' ? `RSS Intel: ${loc.name}` : `TG Intel: ${loc.name}`,
              description: `<b>Source:</b> ${item.sourceName}<br><br>${item.text.substring(0, 150)}...`,
              link: item.link || '',
              media: item.media,
              hasMedia: item.hasMedia,
              mediaType: item.mediaType,
              sourceType: item.sourceType
            })
          }
        })
        
        mapLocations.value = currentLocations
      }
    } catch (e) {
      console.error("Location extraction failed:", e)
    }
  }
}, { deep: true, immediate: true })

function addBlock(type) {
  const newId = Date.now().toString()
  activeBlocks.value.push({
    id: newId,
    type: type,
    config: { channel: '', url: '', active: false }
  })
  isAddingBlock.value = false
}

function addFeedSource(type) {
  const newId = Date.now().toString()
  activeBlocks.value.unshift({
    id: newId,
    type: type,
    config: { channel: '', url: '', active: false },
    tempInput: ''
  })
  isAddingFeedSource.value = false
}

function startFeedBlock(block) {
  if (!block.tempInput) return
  if (block.type === 'telegram_monitor') {
    block.config.channel = block.tempInput
  } else {
    block.config.url = block.tempInput
  }
  block.config.active = true
  block.id = Date.now().toString()
}

function triggerFileInput(id) {
  const input = document.getElementById('file-' + id)
  if (input) input.click()
}

function handleInlineFileUpload(event, block) {
  const file = event.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    block.config.isFile = true
    block.config.fileName = file.name
    block.config.fileData = e.target.result
    block.config.url = ''
    block.config.active = true
    block.id = Date.now().toString()
  }
  reader.readAsText(file)
}

function removeBlock(id) {
  activeBlocks.value = activeBlocks.value.filter(b => b.id !== id)
}

function startRenaming(block) {
  if (!block.config.customName) {
    block.config.customName = block.config.fileName || block.config.channel || block.config.url
  }
  block.isRenaming = true
}

function updateBlockConfig(id, newConfig) {
  const block = activeBlocks.value.find(b => b.id === id)
  if (block) {
    block.config = { ...block.config, ...newConfig }
  }
}
</script>

<template>
  <div class="monitoring-page">
    <div class="header-section flex items-start justify-between">
      <div>
        <h1 class="page-title">{{ t('monitoring.title') }}</h1>
        <p class="page-subtitle">{{ t('monitoring.subtitle') }}</p>
      </div>
      
      <div style="display: flex; gap: 12px; align-items: center;">
        <button class="btn-primary" style="padding: 8px 16px; font-size: var(--text-sm); font-weight: 500; border-radius: var(--radius-md);" @click="summarizeToday" :disabled="isSummarizing || aggregatedFeed.length === 0" :title="$t('monitoring.summarizeAllFeeds')">
          {{ isSummarizing ? '...' : $t('monitoring.aiSummaryTitle') }}
        </button>

        <div class="view-toggles glass-panel">
          <button 
            class="toggle-btn" 
            :class="{ active: viewMode === 'grid' }" 
            @click="viewMode = 'grid'"
            :title="$t('monitoring.gridView')"
          >
            <LayoutGrid size="18" />
          </button>
          <button 
            class="toggle-btn" 
            :class="{ active: viewMode === 'list' }" 
            @click="viewMode = 'list'"
            :title="$t('monitoring.listView')"
          >
            <ListIcon size="18" />
          </button>
        </div>
      </div>
    </div>

    <div class="split-layout">
      <div class="left-panel">
        <!-- Global AI Summary Card (Visible above grid and list) -->
        <div v-if="aiSummary" class="ai-summary-card glass-panel" style="margin-bottom: 24px; width: 100%; border-radius: var(--radius-lg);">
      <div class="ai-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; margin-bottom: 16px;">
        <h4 style="margin: 0; font-size: var(--text-base); font-weight: 500; color: var(--text-main);">{{ $t('monitoring.aiSummaryTitle') }}</h4>
        <div style="display: flex; gap: 8px;">
          <button class="icon-btn" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer;" @click="aiSummaryHidden = !aiSummaryHidden" :title="aiSummaryHidden ? $t('common.show') : $t('common.hide')">
            <ChevronUp v-if="!aiSummaryHidden" size="16" />
            <ChevronDown v-else size="16" />
          </button>
          <button class="icon-btn" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer;" @click="aiSummary = null" :title="$t('common.close')"><X size="16" /></button>
        </div>
      </div>
      <div v-show="!aiSummaryHidden" class="ai-content markdown-body" v-html="aiSummary" style="font-size: var(--text-sm); color: var(--text-main); line-height: var(--line-height-relaxed);"></div>
    </div>

    <div class="blocks-container" v-show="viewMode === 'grid'">
      <draggable
        v-model="activeBlocks"
        item-key="id"
        class="blocks-grid"
        handle=".block-header"
        ghost-class="ghost-block"
      >
        <template #item="{ element }">
          <div class="draggable-wrapper relative group">
            <button class="remove-block-btn" @click="removeBlock(element.id)" :title="t('monitoring.removeBlock')">
              <X size="16" />
            </button>
            <TelegramMonitor
              v-if="element.type === 'telegram_monitor'"
              :config="element.config"
              @update-config="updateBlockConfig(element.id, $event)"
              @update-data="handleFeedData(element.id, $event)"
            />
            <RssMonitor
              v-if="element.type === 'rss_monitor'"
              :config="element.config"
              @update-config="updateBlockConfig(element.id, $event)"
              @update-data="handleFeedData(element.id, $event)"
            />
          </div>
        </template>
        <template #footer>
          <!-- Add Block Selection -->
          <div class="add-block-wrapper">
            <div class="add-block glass-panel group" v-if="!isAddingBlock" @click="isAddingBlock = true">
              <div class="add-icon">
                <Plus size="32" class="text-muted group-hover" />
              </div>
              <span>{{ t('monitoring.addNewBlock') }}</span>
            </div>

            <div class="add-block-menu glass-panel" v-else>
              <h3>{{ t('monitoring.selectBlockType') }}</h3>
              <div class="block-options">
                <button class="block-option" @click="addBlock('telegram_monitor')">
                  <MessageCircle size="24" class="text-orange" />
                  <span>{{ t('monitoring.telegramMonitor') }}</span>
                </button>
                <button class="block-option" @click="addBlock('rss_monitor')">
                  <Rss size="24" class="text-green" style="color: #10B981;" />
                  <span>{{ t('monitoring.rssFeed') }}</span>
                </button>
              </div>
              <button class="btn-cancel" @click="isAddingBlock = false">{{ t('monitoring.cancel') }}</button>
            </div>
          </div>
        </template>
      </draggable>
    </div>

    <!-- Feed Layout -->
    <div class="feed-layout" v-if="viewMode === 'list'">
      <!-- Sidebar -->
      <div class="feed-sidebar glass-panel">
        <div class="sidebar-header">
          <h3>{{ $t('monitoring.allSources') }} <span class="badge">{{ activeBlocks.length }}</span></h3>
        </div>
        <div class="source-list">
          <div v-for="block in activeBlocks" :key="block.id" class="source-item" :class="{ 'flex-col': !block.config.active }">
            
            <!-- Inactive block needs configuration -->
            <template v-if="!block.config.active">
              <div class="mini-input-group">
                <MessageCircle v-if="block.type === 'telegram_monitor'" size="14" class="text-orange flex-shrink-0" />
                <Rss v-if="block.type === 'rss_monitor'" size="14" class="text-green flex-shrink-0" />
                <input 
                  v-model="block.tempInput" 
                  :placeholder="block.type === 'telegram_monitor' ? 'Channel Name' : 'RSS URL'"
                  class="mini-input flex-1"
                  @keyup.enter="startFeedBlock(block)"
                />
                <template v-if="block.type === 'rss_monitor'">
                  <input type="file" :id="'file-' + block.id" accept=".xml,.rss" style="display: none" @change="handleInlineFileUpload($event, block)" />
                  <button @click="triggerFileInput(block.id)" class="text-xs text-muted hover:text-white transition px-2" :title="$t('monitoring.loadLocalFile')">
                    <Upload size="14" />
                  </button>
                </template>
              </div>
              <div class="mini-actions">
                <button @click="removeBlock(block.id)" class="mini-btn-cancel">{{ $t('common.cancel') }}</button>
                <button @click="startFeedBlock(block)" class="mini-btn-start">{{ $t('common.start') }}</button>
              </div>
            </template>
            
            <!-- Active block -->
            <template v-else>
              <MessageCircle v-if="block.type === 'telegram_monitor'" size="14" class="text-orange flex-shrink-0" />
              <Rss v-if="block.type === 'rss_monitor'" size="14" class="text-green flex-shrink-0" />
              
              <div v-if="block.isRenaming" class="flex-1 flex items-center mr-2">
                <input 
                  v-model="block.config.customName" 
                  class="mini-input flex-1 w-full" 
                  style="padding: 2px 6px;"
                  spellcheck="true"
                  @keyup.enter="block.isRenaming = false" 
                  @blur="block.isRenaming = false"
                  @vue:mounted="({ el }) => el.focus()"
                />
              </div>
              <span v-else class="truncate cursor-pointer" style="flex: 1;" @dblclick="startRenaming(block)">
                {{ block.config.customName || block.config.fileName || block.config.channel || block.config.url }}
              </span>

              <button v-if="!block.isRenaming" class="edit-btn flex-shrink-0" @click="startRenaming(block)" :title="$t('common.rename')">
                <Edit2 size="12"/>
              </button>
              <button class="remove-btn flex-shrink-0" @click="removeBlock(block.id)" :title="$t('common.remove')"><X size="12"/></button>
            </template>
            
          </div>
        </div>
        <div class="add-source-section">
          <button class="add-source-btn" v-if="!isAddingFeedSource" @click="isAddingFeedSource = true">
            <Plus size="14" /> {{ $t('monitoring.addNewBlock') }}
          </button>
          <div v-else class="feed-add-menu">
            <button class="feed-add-option" @click="addFeedSource('telegram_monitor')"><MessageCircle size="14" class="text-orange"/> {{ $t('monitoring.telegramMonitor') }}</button>
            <button class="feed-add-option" @click="addFeedSource('rss_monitor')"><Rss size="14" class="text-green"/> {{ $t('monitoring.rssFeed') }}</button>
            <button class="feed-add-cancel" @click="isAddingFeedSource = false">{{ $t('common.cancel') }}</button>
          </div>
        </div>
      </div>

      <!-- Main Feed -->
      <div class="feed-content">
        <div class="feed-search glass-panel">
          <Search size="16" class="text-muted" />
          <input v-model="feedSearch" placeholder="Search anything - actors, sectors, regions, CVEs..." />
        </div>
        <div class="feed-items">
          <div v-for="item in filteredFeed" :key="item.id" class="feed-card glass-panel">
            <div class="feed-card-header">
              <div class="feed-source">
                <span class="source-badge" :class="item.sourceType">
                  <MessageCircle v-if="item.sourceType === 'telegram'" size="10" style="display:inline; margin-right:4px; vertical-align:text-top;"/>
                  <Rss v-if="item.sourceType === 'rss'" size="10" style="display:inline; margin-right:4px; vertical-align:text-top;"/>
                  {{ item.sourceName.toUpperCase() }}
                </span>
              </div>
              <div class="feed-time">{{ item.timeStr }}</div>
            </div>
            <h3 v-if="item.author && item.sourceType === 'rss'" class="feed-title">
              <a :href="item.link" target="_blank">{{ item.author }}</a>
            </h3>
            <h3 v-if="item.sourceType === 'telegram'" class="feed-title text-orange">
              {{ item.author }}
            </h3>
            <p class="feed-body">{{ item.text }}</p>
          </div>
          <div v-if="filteredFeed.length === 0" class="empty-feed">
            No intelligence data available. Configure sources to populate the feed.
          </div>
        </div>
      </div>
      </div>
      
      </div>
      <!-- End of left-panel -->
      
      <!-- Right side: Interactive Map -->
      <div class="right-panel">
        <MonitoringMap :locations="mapLocations" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-right: 8px;
  height: 100%;
  overflow: hidden;
}

.split-layout {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
  height: 100%;
}

.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding-right: 8px;
  min-width: 40%;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 500px;
  min-width: 40%;
}

.header-section {
  margin-bottom: 32px;
}

.page-title {
  font-size: 2rem;
  margin-bottom: 8px;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.blocks-container {
  flex: 1;
}

.blocks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
  align-items: start;
  padding-bottom: 32px;
}

/* Feed Layout Styles */
.feed-layout {
  display: flex;
  gap: 24px;
  flex: 1;
  overflow: hidden;
  padding-bottom: 16px;
}

.feed-sidebar {
  width: 250px;
  display: flex;
  flex-direction: column;

  padding: 16px;
  flex-shrink: 0;
  max-height: 100%;
}

.sidebar-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  font-size: 0.95rem;
  color: var(--text-main);
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badge {
  background: var(--overlay-10);
  padding: 2px 8px;

  font-size: 0.75rem;
}

.source-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
  padding: 8px;
  background: var(--overlay-8);

  transition: var(--transition);
}

.source-item:hover {
  background: var(--overlay-10);
  color: var(--text-main);
}

.remove-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;

  opacity: 0;
  transition: var(--transition);
}

.edit-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;

  opacity: 0;
  transition: var(--transition);
}

.source-item:hover .remove-btn,
.source-item:hover .edit-btn {
  opacity: 1;
}

.remove-btn:hover {
  color: var(--accent-red);
  background: var(--overlay-10);
}

.edit-btn:hover {
  color: var(--text-main);
  background: var(--overlay-10);
}

.add-source-section {
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.add-source-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px;
  background: rgba(var(--accent-rgb), 0.1);
  border: 1px solid rgba(var(--accent-rgb), 0.2);
  color: var(--accent-orange);

  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: var(--transition);
}

.add-source-btn:hover {
  background: rgba(var(--accent-rgb), 0.2);
}

.feed-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.feed-search {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;

}

.feed-search input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 0.95rem;
  outline: none;
}

.feed-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 8px;
}

.feed-card {
  padding: 20px;

  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: var(--transition);
}

.feed-card:hover {
  border-color: var(--border-color);
}

.feed-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feed-source {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 4px 8px;

  display: inline-flex;
  align-items: center;
}

.source-badge.telegram {
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent-orange);
}

.source-badge.rss {
  background: rgba(var(--accent-rgb), 0.15);
  color: var(--accent-green);
}

.feed-time {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.feed-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.feed-title a {
  color: var(--text-main);
  text-decoration: none;
  transition: var(--transition);
}

.feed-title a:hover {
  text-decoration: underline;
}

.feed-body {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-main);
  line-height: 1.5;
}

.empty-feed {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
  background: var(--overlay-8);

  border: 1px dashed var(--border-color);
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flex-col { flex-direction: column; align-items: stretch; }
.flex-shrink-0 { flex-shrink: 0; }
.flex-1 { flex: 1; min-width: 0; }
.cursor-pointer { cursor: pointer; }
.mr-2 { margin-right: 8px; }

.ai-summary-card {
  padding: 16px;
  background: rgba(var(--accent-rgb), 0.05);
  border: 1px solid rgba(var(--accent-rgb), 0.3);
}

.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed rgba(var(--accent-rgb), 0.2);
}

.ai-content {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-main);
}

.ai-content :deep(h1), .ai-content :deep(h2), .ai-content :deep(h3) {
  font-size: 1.05rem;
  margin-top: 12px;
  margin-bottom: 8px;
  color: var(--accent-orange);
}

.ai-content :deep(p) { margin-bottom: 10px; }
.ai-content :deep(ul) { margin-left: 20px; margin-bottom: 10px; list-style-type: disc; }
.ai-content :deep(li) { margin-bottom: 4px; }

.mini-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.mini-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  width: 100%;
  margin-top: 8px;
}

.mini-btn-cancel {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.75rem;
  cursor: pointer;
  transition: var(--transition);
}

.mini-btn-cancel:hover {
  color: var(--text-main);
}

.mini-btn-start {
  background: transparent;
  border: none;
  color: var(--accent-orange);
  font-weight: 700;
  font-size: 0.75rem;
  cursor: pointer;
  transition: var(--transition);
}

.mini-btn-start:hover {
  color: var(--text-main);
}

.mini-input {
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 4px 8px;

  font-size: 0.8rem;
  outline: none;
}

.feed-add-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feed-add-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);

  color: var(--text-main);
  cursor: pointer;
  font-size: 0.85rem;
  transition: var(--transition);
}

.feed-add-option:hover {
  background: var(--overlay-10);
}

.feed-add-cancel {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.8rem;
  padding: 4px;
}

.feed-add-cancel:hover {
  color: var(--text-main);
}

.view-toggles {
  display: flex;
  padding: 4px;

  gap: 4px;
}

.toggle-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 8px;

  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  color: var(--text-main);
  background: var(--overlay-8);
}

.toggle-btn.active {
  color: var(--accent-orange);
  background: rgba(var(--accent-rgb), 0.1);
}

.draggable-wrapper {
  height: 100%;
  position: relative;
}

.remove-block-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--bg-panel);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  width: 28px;
  height: 28px;

  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  opacity: 0;
  transition: var(--transition);
  cursor: pointer;
}

.draggable-wrapper:hover .remove-block-btn {
  opacity: 1;
}

.remove-block-btn:hover {
  background: var(--overlay-10);
  color: var(--accent-red);
  border-color: var(--accent-red);
}

/* When a block is being dragged */
.ghost-block {
  opacity: 0.4;
  background: rgba(var(--accent-rgb), 0.1);
  border: 1px dashed var(--accent-orange);

}

.add-block-wrapper {
  height: 100%;
}

/* Add Block Style */
.add-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  height: 100%;
  min-height: 300px;
  border: 2px dashed var(--overlay-10);
  background: var(--overlay-8);
  cursor: pointer;
  color: var(--text-muted);

  transition: var(--transition);
}

.add-block:hover {
  background: rgba(var(--accent-rgb), 0.02);
  border-color: rgba(var(--accent-rgb), 0.2);
  color: var(--accent-orange);
}

.add-icon {
  width: 64px;
  height: 64px;

  background: var(--overlay-8);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
}

.add-block:hover .add-icon {
  background: rgba(var(--accent-rgb), 0.1);
}

.add-block:hover .group-hover {
  color: var(--accent-orange);
}

/* Block Selection Menu */
.add-block-menu {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  height: 100%;
  min-height: 300px;
  border: 2px dashed var(--border-color);

  padding: 24px;
}

.add-block-menu h3 {
  font-size: 1.1rem;
  color: var(--text-main);
  margin: 0;
}

.block-options {
  display: flex;
  gap: 16px;
  width: 100%;
}

.block-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  color: var(--text-main);
  cursor: pointer;
  transition: var(--transition);
}

.block-option:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
  transform: translateY(-2px);
}

.btn-cancel {
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  transition: var(--transition);
}

.btn-cancel:hover {
  color: var(--text-main);
}

</style>
