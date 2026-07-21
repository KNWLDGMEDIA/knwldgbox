<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { LayoutGrid, Download, Image as ImageIcon, Settings, X, Loader2 } from 'lucide-vue-next'

const { t } = useI18n()

const files = ref([])
const numColumns = ref(4)
const watermarkText = ref("")
const blurImages = ref(false)
const blurRadius = ref(15)

const bgColor = ref("#0A0A0A")
const watermarkColor = ref("#FFA500")
const watermarkOpacity = ref(60)
const watermarkSize = ref(45)

const isGenerating = ref(false)
const resultUrl = ref(null)
const errorMsg = ref(null)

const API_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api`

function handleFileSelect(event) {
  const selectedFiles = Array.from(event.target.files)
  
  // Filter for images only
  const validFiles = selectedFiles.filter(file => file.type.startsWith('image/'))
  
  // Add preview URLs
  const filesWithPreview = validFiles.map(file => {
    return {
      file,
      preview: URL.createObjectURL(file),
      id: Math.random().toString(36).substring(7)
    }
  })
  
  files.value.push(...filesWithPreview)
}

function removeFile(id) {
  const index = files.value.findIndex(f => f.id === id)
  if (index !== -1) {
    URL.revokeObjectURL(files.value[index].preview)
    files.value.splice(index, 1)
  }
}

async function generateCollage() {
  if (files.value.length === 0) return
  
  isGenerating.value = true
  errorMsg.value = null
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
  
  try {
    const formData = new FormData()
    files.value.forEach(item => {
      formData.append('files', item.file)
    })
    
    formData.append('num_columns', numColumns.value)
    formData.append('watermark_text', watermarkText.value)
    formData.append('blur_images', blurImages.value)
    formData.append('blur_radius', blurRadius.value)
    formData.append('bg_color_hex', bgColor.value)
    formData.append('watermark_color_hex', watermarkColor.value)
    formData.append('watermark_opacity', watermarkOpacity.value)
    formData.append('watermark_size', watermarkSize.value)
    
    const response = await fetch(`${API_BASE}/collage/generate`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to generate collage')
    }
    
    const blob = await response.blob()
    resultUrl.value = URL.createObjectURL(blob)
    
  } catch (err) {
    errorMsg.value = err.message
  } finally {
    isGenerating.value = false
  }
}
</script>

<template>
  <div class="collage-module">
    <div class="collage-container">
      
      <!-- LEFT PANEL: Settings & Upload -->
      <div class="settings-panel glass-panel">
        <h2 class="panel-title"><Settings size="18" /> {{ t('knwldgTools.collage.config') }}</h2>
        
        <div class="form-group">
          <label>{{ t('knwldgTools.collage.numColumns') }}</label>
          <input type="number" v-model="numColumns" min="1" max="10" class="input-field" />
        </div>
        
        <div class="form-group row-group-between">
          <label>{{ t('knwldgTools.collage.bgColor') }}</label>
          <input type="color" v-model="bgColor" class="color-picker" />
        </div>
        
        <div class="form-group">
          <label>{{ t('knwldgTools.collage.watermarkText') }}</label>
          <input type="text" v-model="watermarkText" :placeholder="t('knwldgTools.collage.watermarkPlaceholder')" class="input-field" />
        </div>
        
        <div v-if="watermarkText" class="advanced-watermark-settings glass-panel-inner">
          <div class="form-group row-group-between">
            <label>{{ t('knwldgTools.collage.color') }}</label>
            <input type="color" v-model="watermarkColor" class="color-picker" />
          </div>
          
          <div class="form-group">
            <div class="label-flex">
              <label>{{ t('knwldgTools.collage.opacity') }}</label>
              <span class="value-badge">{{ watermarkOpacity }}</span>
            </div>
            <input type="range" v-model="watermarkOpacity" min="10" max="255" class="range-slider" />
          </div>
          
          <div class="form-group">
            <div class="label-flex">
              <label>{{ t('knwldgTools.collage.size') }}</label>
              <span class="value-badge">{{ watermarkSize }}px</span>
            </div>
            <input type="range" v-model="watermarkSize" min="10" max="150" class="range-slider" />
          </div>
        </div>
        
        <div class="form-group row-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="blurImages" />
            {{ t('knwldgTools.collage.blurImages') }}
          </label>
        </div>
        
        <div class="form-group" v-if="blurImages">
          <label>{{ t('knwldgTools.collage.blurRadius') }}</label>
          <input type="number" v-model="blurRadius" min="1" max="50" class="input-field" />
        </div>

        <div class="upload-section">
          <label class="upload-btn">
            <ImageIcon size="20" />
            <span>{{ t('knwldgTools.collage.selectImages') }}</span>
            <input type="file" multiple accept="image/*" @change="handleFileSelect" hidden />
          </label>
          <p class="upload-hint">{{ t('knwldgTools.collage.imagesSelected', { count: files.length }) }}</p>
        </div>

        <div class="image-preview-grid" v-if="files.length > 0">
          <div v-for="item in files" :key="item.id" class="preview-item">
            <img :src="item.preview" />
            <button class="remove-btn" @click="removeFile(item.id)">
              <X size="14" />
            </button>
          </div>
        </div>

        <button 
          class="btn-generate" 
          @click="generateCollage" 
          :disabled="files.length === 0 || isGenerating"
        >
          <Loader2 v-if="isGenerating" size="20" class="spin" />
          <LayoutGrid v-else size="20" />
          <span>{{ isGenerating ? t('knwldgTools.collage.generating') : t('knwldgTools.collage.generate') }}</span>
        </button>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </div>

      <!-- RIGHT PANEL: Result -->
      <div class="result-panel glass-panel">
        <div v-if="!resultUrl && !isGenerating" class="empty-result">
          <LayoutGrid size="48" class="empty-icon" />
          <h3>{{ t('knwldgTools.collage.noCollage') }}</h3>
          <p>{{ t('knwldgTools.collage.uploadHint') }}</p>
        </div>
        
        <div v-else-if="isGenerating" class="empty-result">
          <Loader2 size="48" class="empty-icon spin" />
          <h3>{{ t('knwldgTools.collage.processing') }}</h3>
          <p>{{ t('knwldgTools.collage.processingHint') }}</p>
        </div>
        
        <div v-else-if="resultUrl" class="result-view">
          <div class="result-actions">
            <h3>{{ t('knwldgTools.collage.generated') }}</h3>
            <a :href="resultUrl" download="pro_collage.png" class="btn-download">
              <Download size="16" />
              {{ t('knwldgTools.collage.download') }}
            </a>
          </div>
          
          <div class="result-image-wrapper">
            <img :src="resultUrl" class="result-image" alt="Generated Collage" />
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.collage-module {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.collage-container {
  display: flex;
  gap: 20px;
  flex: 1;
  align-items: flex-start;
}
@media (max-width: 900px) {
  .collage-container { flex-direction: column; }
}

.settings-panel {
  flex: 1;
  max-width: 400px;
  padding: 20px;

  display: flex;
  flex-direction: column;
  gap: 20px;
}
@media (max-width: 900px) {
  .settings-panel { max-width: 100%; width: 100%; }
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.2rem;
  margin: 0;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 0.9rem;
  color: var(--text-muted);
}
.input-field {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 10px;

  color: var(--text-main);
}
.row-group { flex-direction: row; align-items: center; }
.row-group-between { flex-direction: row; align-items: center; justify-content: space-between; }

.color-picker {
  -webkit-appearance: none;
  border: 1px solid var(--border-color);
  width: 40px;
  height: 40px;

  padding: 0;
  cursor: pointer;
  background: transparent;
}
.color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.color-picker::-webkit-color-swatch { border: none; border-radius: 5px; }

.glass-panel-inner {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 12px;

  display: flex;
  flex-direction: column;
  gap: 12px;
}

.label-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.value-badge {
  background: var(--overlay-10);
  padding: 2px 6px;

  font-size: 0.75rem;
  color: var(--accent-orange);
}

.range-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  background: var(--overlay-10);

  outline: none;
}
.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;

  background: var(--accent-orange);
  cursor: pointer;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-main) !important;
}

.upload-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}
.upload-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--overlay-10);
  padding: 10px 16px;

  cursor: pointer;
  transition: all 0.2s;
  border: 1px dashed var(--border-color);
}
.upload-btn:hover {   background: var(--overlay-10); border-color: var(--accent-orange); }
.upload-hint { font-size: 0.85rem; color: var(--text-muted); }

.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}
.preview-item {
  position: relative;
  aspect-ratio: 1;

  overflow: hidden;
}
.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.remove-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  background: rgba(0,0,0,0.7);
  color: var(--text-main);
  border: none;

  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}
.remove-btn:hover { background: var(--accent-red); }

.btn-generate {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--accent-orange);
  color: #000;
  border: none;
  padding: 14px;

  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  transition: all 0.2s;
}
.btn-generate:hover:not(:disabled) { filter: brightness(1.15); transform: translateY(-2px); }
.btn-generate:disabled { opacity: 0.5; cursor: not-allowed; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.error-msg { color: var(--accent-red); font-size: 0.9rem; text-align: center; }

.result-panel {
  flex: 2;
  padding: 20px;

  display: flex;
  flex-direction: column;
  min-height: 400px;
}

.empty-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);
}
.empty-icon { opacity: 0.3; margin-bottom: 16px; }

.result-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}
.result-actions h3 { margin: 0; }
.btn-download {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--accent-purple);
  color: #fff;
  padding: 8px 16px;

  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
}
.btn-download:hover { filter: brightness(1.1); transform: scale(1.05); }

.result-image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-panel);

  padding: 16px;
  overflow: auto;
}
.result-image {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;

}
</style>
