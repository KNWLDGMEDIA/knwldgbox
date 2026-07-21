<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ImageOff, Download, Image as ImageIcon, X, Loader2 } from 'lucide-vue-next'

const { t } = useI18n()

const selectedFile = ref(null)
const previewUrl = ref(null)

const colorHex = ref('#FF0000')
const thickness = ref(3)

const isGenerating = ref(false)
const resultUrl = ref(null)
const errorMsg = ref(null)

const API_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api`

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file || !file.type.startsWith('image/')) return
  
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  
  // Clear previous result
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
  errorMsg.value = null
}

function removeFile() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value = null
  previewUrl.value = null
  if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
  resultUrl.value = null
}

async function generateCross() {
  if (!selectedFile.value) return
  
  isGenerating.value = true
  errorMsg.value = null
  
  if (resultUrl.value) {
    URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = null
  }
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('color_hex', colorHex.value)
    formData.append('thickness', thickness.value)
    
    const response = await fetch(`${API_BASE}/debunk`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to generate debunk image')
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
  <div class="cross-module">
    <div class="cross-container">
      
      <!-- LEFT PANEL: Upload & Action -->
      <div class="settings-panel glass-panel">
        <h2 class="panel-title"><ImageOff size="18" /> {{ t('knwldgTools.cross.config') }}</h2>
        
        <p class="panel-desc">Upload a fake or manipulated image to automatically apply a red cross overlay, marking it as debunked.</p>

        <div class="upload-section" v-if="!selectedFile">
          <label class="upload-area">
            <ImageIcon size="32" class="text-muted" />
            <span class="upload-text">{{ t('knwldgTools.cross.selectImage') }}</span>
            <input type="file" accept="image/*" @change="handleFileSelect" hidden />
          </label>
        </div>

        <div class="preview-section" v-else>
          <div class="image-preview">
            <img :src="previewUrl" alt="Selected" />
            <button class="remove-btn" @click="removeFile">
              <X size="16" />
            </button>
          </div>
        </div>

        <div class="form-group row-group-between mt-4">
          <label>{{ t('knwldgTools.cross.lineColor') }}</label>
          <input type="color" v-model="colorHex" class="color-picker" />
        </div>

        <div class="form-group">
          <div class="label-flex">
            <label>{{ t('knwldgTools.cross.lineThickness') }}</label>
            <span class="value-badge">{{ thickness }}%</span>
          </div>
          <input type="range" v-model="thickness" min="1" max="25" step="0.5" class="range-slider" />
        </div>


        <button 
          class="btn-generate" 
          @click="generateCross" 
          :disabled="!selectedFile || isGenerating"
        >
          <Loader2 v-if="isGenerating" size="20" class="spin" />
          <ImageOff v-else size="20" />
          <span>{{ isGenerating ? t('knwldgTools.cross.generating') : t('knwldgTools.cross.generate') }}</span>
        </button>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </div>

      <!-- RIGHT PANEL: Result -->
      <div class="result-panel glass-panel">
        <div v-if="!resultUrl && !isGenerating" class="empty-result">
          <ImageOff size="48" class="empty-icon" />
          <h3>{{ t('knwldgTools.cross.noImage') }}</h3>
          <p>{{ t('knwldgTools.cross.uploadHint') }}</p>
        </div>
        
        <div v-else-if="isGenerating" class="empty-result">
          <Loader2 size="48" class="empty-icon spin" />
          <h3>{{ t('knwldgTools.cross.processing') }}</h3>
        </div>
        
        <div v-else-if="resultUrl" class="result-view">
          <div class="result-actions">
            <h3>{{ t('knwldgTools.cross.generated') }}</h3>
            <a :href="resultUrl" download="crossed_image.png" class="btn-download">
              <Download size="16" />
              {{ t('knwldgTools.cross.download') }}
            </a>
          </div>
          
          <div class="result-image-wrapper">
            <img :src="resultUrl" class="result-image" alt="Crossed Image" />
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.cross-module {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.cross-container {
  display: flex;
  gap: 20px;
  flex: 1;
  align-items: flex-start;
}
@media (max-width: 900px) {
  .cross-container { flex-direction: column; }
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

.panel-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg-panel);
  border: 2px dashed var(--border-color);

  padding: 40px 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  background: var(--overlay-8);
  border-color: var(--accent-orange);
}

.upload-text {
  font-size: 0.95rem;
  color: var(--text-main);
}

.mt-4 { margin-top: 16px; }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 0.9rem;
  color: var(--text-muted);
}
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
  margin-top: 8px;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;

  background: var(--accent-red);
  cursor: pointer;
}

.preview-section {
  width: 100%;
}

.image-preview {
  position: relative;
  width: 100%;

  overflow: hidden;
  background: var(--bg-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
}

.image-preview img {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.remove-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0,0,0,0.7);
  color: var(--text-main);
  border: none;

  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
}

.remove-btn:hover {
  background: var(--accent-red);
}

.btn-generate {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--accent-red);
  color: #fff;
  border: none;
  padding: 14px;

  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  transition: all 0.2s;
}

.btn-generate:hover:not(:disabled) { 
  background: #ff3333; 
  transform: translateY(-2px); 

}
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
  background: var(--accent-green);
  color: #000;
  padding: 8px 16px;

  text-decoration: none;
  font-weight: 600;
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
