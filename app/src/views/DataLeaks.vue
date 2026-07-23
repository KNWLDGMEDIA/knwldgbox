<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import draggable from 'vuedraggable'
import { Plus, X, Database, ShieldAlert, Rss } from 'lucide-vue-next'
import LeakMonitor from '../components/LeakMonitor.vue'
import PwnedChecker from '../components/PwnedChecker.vue'
import RssMonitor from '../components/RssMonitor.vue'

const { t } = useI18n()

const STORAGE_KEY = 'knwldg_dataleaks_blocks'

const activeBlocks = ref([])

onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && saved !== '[]') {
    try {
      const parsed = JSON.parse(saved)
      // Clean up legacy blocks that are now permanent
      activeBlocks.value = parsed.filter(b => b.type === 'rss_monitor')
    } catch (e) {
      activeBlocks.value = []
    }
  } else {
    activeBlocks.value = []
  }
})

// Watch for deep changes in blocks (reordering or config changes)
watch(activeBlocks, (newVal) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
}, { deep: true })

const isAddingBlock = ref(false)

function addBlock(type) {
  const newId = Date.now().toString()
  activeBlocks.value.push({
    id: newId,
    type: type,
    config: { active: false }
  })
  isAddingBlock.value = false
}

function removeBlock(id) {
  activeBlocks.value = activeBlocks.value.filter(b => b.id !== id)
}

function updateBlockConfig(id, newConfig) {
  const block = activeBlocks.value.find(b => b.id === id)
  if (block) {
    block.config = { ...block.config, ...newConfig }
  }
}
</script>

<template>
  <div class="dataleaks-page">
    <div class="header-section">
      <h1 class="page-title">{{ t('dataLeaks.title') }}</h1>
      <p class="page-subtitle">{{ t('dataLeaks.subtitle') }}</p>
    </div>

    <div class="permanent-blocks blocks-grid">
      <LeakMonitor :config="{ active: true }" />
      <PwnedChecker :config="{ email: '' }" />
    </div>

    <div class="blocks-container">
      <draggable
        v-model="activeBlocks"
        item-key="id"
        class="blocks-grid"
        handle=".block-header"
        ghost-class="ghost-block"
      >
        <template #item="{ element }">
          <div class="draggable-wrapper relative group" v-if="element.type === 'rss_monitor'">
            <button class="remove-block-btn" @click="removeBlock(element.id)" :title="t('dataLeaks.removeBlock')">
              <X size="16" />
            </button>
            <RssMonitor
              :config="element.config"
              @update-config="updateBlockConfig(element.id, $event)"
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
              <span>{{ t('dataLeaks.addNewBlock') }}</span>
            </div>

            <div class="add-block-menu glass-panel" v-else>
              <h3>{{ t('dataLeaks.selectTool') }}</h3>
              <div class="block-options">
                <button class="block-option" @click="addBlock('rss_monitor')">
                  <Rss size="24" class="text-orange" style="color: #F97316;" />
                  <span>{{ t('dataLeaks.customRssFeed') }}</span>
                </button>
              </div>
              <button class="btn-cancel" @click="isAddingBlock = false">{{ t('dataLeaks.cancel') }}</button>
            </div>
          </div>
        </template>
      </draggable>
    </div>
  </div>
</template>

<style scoped>
.dataleaks-page {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
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
}

.permanent-blocks {
  margin-bottom: 24px;
}

.blocks-container .blocks-grid {
  padding-bottom: 32px;
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
  background: var(--overlay-10);
  border: 1px dashed var(--accent-red);

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
  border: 2px dashed var(--border-color);
  background: var(--overlay-8);
  cursor: pointer;
  color: var(--text-muted);

  transition: var(--transition);
}

.add-block:hover {
  background: var(--overlay-10);
  border-color: var(--accent-red);
  color: var(--accent-red);
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
  background: rgba(239, 68, 68, 0.1);
}

.add-block:hover .group-hover {
  color: var(--accent-red);
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
  background: var(--overlay-8);
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
