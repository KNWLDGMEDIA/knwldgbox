<script setup>
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { VueFlow, useVueFlow, Handle, Position, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { NodeResizer } from '@vue-flow/node-resizer'
import { User, Building, Mail, Phone, Plus, Trash2, Link, ArrowRight, ArrowLeftRight, Minus, Activity, Spline, Slash, CornerDownRight, X, Save, Check, FolderOpen, FileText, PanelLeftClose, PanelLeftOpen, Download, Upload, Globe, Image as ImageIcon, MapPin, Hash, Monitor, Search, Database, CreditCard, Box, FileKey, Shield, Square, Grid } from 'lucide-vue-next'
import { marked } from 'marked'
const availableIcons = {
  User, Building, Mail, Phone, Globe, ImageIcon, MapPin, Hash, Monitor, 
  Search, Link, FileText, Database, CreditCard, Box, FileKey, Shield
}


// Import Vue Flow styles
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/node-resizer/dist/style.css'

const { t } = useI18n()
const { onConnect, addEdges, onEdgeClick, onPaneClick, onNodeClick, toObject, onNodeDragStart, onNodeDrag, onNodeDragStop, screenToFlowCoordinate, project } = useVueFlow()

const files = ref([])
const activeFile = ref(null)
const editingFilename = ref(null)
const newFilename = ref('')

const nodes = ref([])
const edges = ref([])
const nextNodeId = ref(1)

const editingNodeId = ref(null)
const selectedNode = ref(null)
const saveSuccess = ref(false)
const isSidebarVisible = ref(window.innerWidth > 768)
const snapToGrid = ref(false)

const showDeleteModal = ref(false)
const fileToDelete = ref(null)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  edgeId: null,
  label: ''
})

let isSwitching = false


onMounted(async () => {
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs`)
    if (res.ok) {
      const data = await res.json()
      if (data.graphs && data.graphs.length > 0) {
        files.value = data.graphs
        loadGraph(files.value[0].filename)
        return
      }
    }
  } catch (e) {
    console.error("Failed to fetch graphs from backend", e)
  }
  createNewGraph()
})

window.addEventListener('graph-updated', () => {
  if (activeFile.value) {
    loadGraph(activeFile.value.filename, true)
  } else {
    fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs`)
      .then(res => res.json())
      .then(data => {
        if (data.graphs && data.graphs.length > 0) {
          files.value = data.graphs
          loadGraph(files.value[0].filename)
        }
      })
  }
})

import { onActivated } from 'vue'
onActivated(() => {
  if (activeFile.value) {
    loadGraph(activeFile.value.filename, true)
  }
})

async function createNewGraph() {
  const newName = `investigation_${Date.now()}`
  const newGraph = { filename: newName + '.json', name: newName }
  const payload = { nodes: [], edges: [], nextNodeId: 1 }
  
  try {
    await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${newGraph.filename}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    files.value.push(newGraph)
    loadGraph(newGraph.filename)
  } catch(e) {
    console.error("Failed to create new graph on backend", e)
  }
}

async function loadGraph(filename, force = false) {
  if (!force && activeFile.value?.filename === filename) return
  
  isSwitching = true
  
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${filename}`)
    if (res.ok) {
      const { data } = await res.json()
      nodes.value = data.nodes || []
      edges.value = data.edges || []
      nextNodeId.value = data.nextNodeId || 1
      selectedNode.value = null
      
      const targetFile = files.value.find(f => f.filename === filename)
      if (targetFile) {
        activeFile.value = targetFile
      } else {
        activeFile.value = { filename, name: filename.replace('.json', '') }
        files.value.push(activeFile.value)
      }
    }
  } catch (e) {
    console.error("Failed to load graph", e)
  }
  
  setTimeout(() => { isSwitching = false }, 100)
}

async function closeGraph(filename) {
  fileToDelete.value = filename
  showDeleteModal.value = true
}

async function confirmDeleteGraph() {
  const filename = fileToDelete.value
  if (!filename) return
  
  showDeleteModal.value = false
  
  try {
    await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${filename}`, { method: 'DELETE' })
    files.value = files.value.filter(f => f.filename !== filename)
    if (activeFile.value?.filename === filename) {
      activeFile.value = null
      nodes.value = []
      edges.value = []
      if (files.value.length > 0) {
        loadGraph(files.value[0].filename)
      } else {
        createNewGraph()
      }
    }
  } catch(e) {
    console.error("Failed to delete graph", e)
  }
}

function startRename(file) {
  editingFilename.value = file.filename
  newFilename.value = file.name
}

async function confirmRename(file) {
  if (!newFilename.value.trim() || newFilename.value === file.name) {
    editingFilename.value = null
    return
  }
  
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${file.filename}/rename`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ newName: newFilename.value })
    })
    
    if (res.ok) {
      const { filename: newBackendName } = await res.json()
      const targetFile = files.value.find(f => f.filename === file.filename)
      if (targetFile) {
        targetFile.name = newFilename.value
        targetFile.filename = newBackendName
      }
      if (activeFile.value && activeFile.value.filename === file.filename) {
        activeFile.value.filename = newBackendName
        activeFile.value.name = newFilename.value
      }
    } else {
      alert("Rename failed. Name might already exist.")
    }
  } catch(e) {
    console.error("Failed to rename", e)
  }
  editingFilename.value = null
}

async function exportGraph() {
  if (!activeFile.value) return
  const flow = toObject()
  const payload = {
    nodes: flow.nodes || [],
    edges: flow.edges || [],
    nextNodeId: nextNodeId.value
  }
  const content = JSON.stringify(payload, null, 2)
  
  try {
    if (window.showSaveFilePicker) {
      // Shows native OS "Save As" dialog
      const fileHandle = await window.showSaveFilePicker({
        suggestedName: activeFile.value.filename,
        types: [{
          description: 'JSON Graph File',
          accept: { 'application/json': ['.json'] },
        }],
      })
      const writable = await fileHandle.createWritable()
      await writable.write(content)
      await writable.close()
      
      const newName = fileHandle.name
      activeFile.value.filename = newName
      activeFile.value.name = newName.replace('.json', '')
      localStorage.setItem('knwldg_open_graphs', JSON.stringify(files.value))
    } else {
      // Fallback for Firefox/Safari
      const blob = new Blob([content], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = activeFile.value.filename
      a.click()
      URL.revokeObjectURL(url)
    }
    
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 2000)
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('Failed to save file:', err)
      alert("Save failed or cancelled.")
    }
  }
}

function triggerFileInput() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const data = JSON.parse(e.target.result)
        const filename = file.name
        const newGraph = {
          filename,
          name: filename.replace('.json', '')
        }
        
        const payload = {
          nodes: data.nodes || [],
          edges: data.edges || [],
          nextNodeId: data.nextNodeId || 1
        }
        
        await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${filename}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        
        if (!files.value.find(f => f.filename === filename)) {
          files.value.push(newGraph)
        }
        loadGraph(filename)
      } catch (err) {
        console.error("Failed to parse JSON", err)
        alert("Invalid Graph JSON file.")
      }
    }
    reader.readAsText(file)
  }
  input.click()
}

// Auto-save when flow changes
let autoSaveTimeout = null
watch([nodes, edges], () => {
  if (isSwitching || !activeFile.value) return
  
  const payload = {
    nodes: nodes.value,
    edges: edges.value,
    nextNodeId: nextNodeId.value
  }
  
  if (autoSaveTimeout) clearTimeout(autoSaveTimeout)
  autoSaveTimeout = setTimeout(async () => {
    try {
      await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs/${activeFile.value.filename}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
    } catch(e) {
      console.error("Auto-save failed", e)
    }
  }, 1000)
}, { deep: true })

onConnect((params) => {
  params.id = `edge_${Date.now()}`
  params.animated = false
  params.markerEnd = MarkerType.ArrowClosed
  params.style = { stroke: '#FF7700', strokeWidth: 2 }
  addEdges([params])
})

onEdgeClick((event) => {
  contextMenu.value = {
    visible: true,
    x: event.event.clientX,
    y: event.event.clientY,
    edgeId: event.edge.id,
    label: event.edge.label || ''
  }
})

onPaneClick(() => {
  contextMenu.value.visible = false
  editingNodeId.value = null
  selectedNode.value = null
})

onNodeClick((event) => {
  contextMenu.value.visible = false
  const nodeRef = nodes.value.find(n => n.id === event.node.id)
  if (nodeRef) {
    selectedNode.value = nodeRef
  }
})

let groupChildren = []

onNodeDragStart(({ node }) => {
  if (node.type === 'group') {
    const groupBounds = {
      left: node.position.x,
      right: node.position.x + (node.dimensions?.width || node.style?.width || 400),
      top: node.position.y,
      bottom: node.position.y + (node.dimensions?.height || node.style?.height || 300)
    }
    
    groupChildren = nodes.value.filter(n => {
      if (n.id === node.id || n.type === 'group') return false
      const nLeft = n.position.x
      const nRight = n.position.x + (n.dimensions?.width || 150)
      const nTop = n.position.y
      const nBottom = n.position.y + (n.dimensions?.height || 50)
      return nLeft >= groupBounds.left && nRight <= groupBounds.right && nTop >= groupBounds.top && nBottom <= groupBounds.bottom
    }).map(n => ({ id: n.id, offsetX: n.position.x - node.position.x, offsetY: n.position.y - node.position.y }))
  }
})

onNodeDrag(({ node }) => {
  if (node.type === 'group' && groupChildren.length > 0) {
    nodes.value = nodes.value.map(n => {
      const child = groupChildren.find(c => c.id === n.id)
      if (child) {
        return {
          ...n,
          position: {
            x: node.position.x + child.offsetX,
            y: node.position.y + child.offsetY
          }
        }
      }
      return n
    })
  }
})

onNodeDragStop(() => {
  groupChildren = []
})

function changeSelectedEdgeColor(color) {
  if (contextMenu.value.edgeId) {
    edges.value = edges.value.map(edge => {
      if (edge.id === contextMenu.value.edgeId) {
        return {
          ...edge,
          style: { ...edge.style, stroke: color }
        }
      }
      return edge
    })
  }
}

function updateSelectedEdgeLabel(text) {
  if (contextMenu.value.edgeId) {
    edges.value = edges.value.map(edge => {
      if (edge.id === contextMenu.value.edgeId) {
        return {
          ...edge,
          label: text,
          labelStyle: { fill: '#fff', fontWeight: 600 },
          labelBgStyle: { fill: '#1a1a1a', fillOpacity: 0.9 },
          labelBgPadding: [6, 4],
          labelBgBorderRadius: 4
        }
      }
      return edge
    })
  }
}

function changeEdgeStyle(styleType) {
  if (contextMenu.value.edgeId) {
    edges.value = edges.value.map(edge => {
      if (edge.id === contextMenu.value.edgeId) {
        let newEdge = { ...edge }
        if (styleType === 'uni') {
          newEdge.markerEnd = MarkerType.ArrowClosed
          newEdge.markerStart = undefined
          newEdge.animated = false
        } else if (styleType === 'bi') {
          newEdge.markerEnd = MarkerType.ArrowClosed
          newEdge.markerStart = MarkerType.ArrowClosed
          newEdge.animated = false
        } else if (styleType === 'none') {
          newEdge.markerEnd = undefined
          newEdge.markerStart = undefined
          newEdge.animated = false
        } else if (styleType === 'animated') {
          newEdge.animated = true
        }
        return newEdge
      }
      return edge
    })
  }
}

function changeEdgePathType(pathType) {
  if (contextMenu.value.edgeId) {
    edges.value = edges.value.map(edge => {
      if (edge.id === contextMenu.value.edgeId) {
        return {
          ...edge,
          type: pathType
        }
      }
      return edge
    })
  }
}

function getCenterPosition() {
  try {
    const el = document.querySelector('.vue-flow')
    if (el) {
      const bounds = el.getBoundingClientRect()
      const offset = (Math.random() - 0.5) * 50 // Slight randomness to avoid perfect overlap
      if (typeof screenToFlowCoordinate === 'function') {
        const x = bounds.left + bounds.width / 2
        const y = bounds.top + bounds.height / 2
        return screenToFlowCoordinate({ x: x + offset, y: y + offset })
      } else if (typeof project === 'function') {
        return project({ x: bounds.width / 2 + offset, y: bounds.height / 2 + offset })
      }
    }
  } catch (e) {
    console.error("Failed to compute center", e)
  }
  return { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 }
}

function addNode() {
  const newNode = {
    id: `node_${nextNodeId.value++}`,
    type: 'custom',
    position: getCenterPosition(),
    data: { label: t('network.newNode'), iconName: 'Box', color: '#3B82F6', notes: '' }
  }
  nodes.value.push(newNode)
}

function addGroup() {
  const newGroup = {
    id: `group_${nextNodeId.value++}`,
    type: 'group',
    position: getCenterPosition(),
    style: { width: 400, height: 300, zIndex: -1 },
    data: { label: t('network.untitledGroup'), color: '#6B7280' }
  }
  nodes.value.push(newGroup)
}

function deleteSelected() {
  const selectedNodeIds = nodes.value.filter(n => n.selected).map(n => n.id)
  const selectedEdgeIds = edges.value.filter(e => e.selected).map(e => e.id)
  
  if (selectedNodeIds.length > 0) {
    nodes.value = nodes.value.filter(n => !selectedNodeIds.includes(n.id))
    edges.value = edges.value.filter(e => !selectedNodeIds.includes(e.source) && !selectedNodeIds.includes(e.target))
    if (selectedNode.value && selectedNodeIds.includes(selectedNode.value.id)) {
      selectedNode.value = null
    }
  }
  if (selectedEdgeIds.length > 0) {
    edges.value = edges.value.filter(e => !selectedEdgeIds.includes(e.id))
  }
}

function onKeyDown(e) {
  if ((e.key === 'Delete' || e.key === 'Backspace') && editingNodeId.value === null && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'INPUT') {
    deleteSelected()
  }
}
</script>

<template>
  <div class="graph-page">
    <div class="header-section">
      <h1 class="page-title">{{ $t('network.title') }}</h1>
      <p class="page-subtitle">{{ $t('network.subtitle') }}</p>
    </div>

    <div class="graph-layout">
      <!-- File Explorer Sidebar -->
      <div class="file-explorer glass-panel" v-show="isSidebarVisible">
        <div class="explorer-header">
          <div class="flex items-center gap-2 font-semibold">
            <FolderOpen size="16" class="text-orange" />
            <span>{{ $t('network.openGraphs') }}</span>
          </div>
          <div class="flex items-center gap-1">
            <button class="icon-btn" @click="triggerFileInput" title="Load Graph from Disk">
              <Upload size="16" />
            </button>
            <button class="icon-btn" @click="createNewGraph" title="New Graph">
              <Plus size="16" />
            </button>
          </div>
        </div>
        
        <div class="file-list custom-scrollbar">
          <div 
            v-for="file in files" 
            :key="file.filename"
            class="file-item"
            :class="{ active: activeFile?.filename === file.filename }"
            @click="loadGraph(file.filename)"
            @dblclick="startRename(file)"
          >
            <FileText size="14" class="file-icon" />
            <input 
              v-if="editingFilename === file.filename"
              v-model="newFilename"
              class="rename-input"
              @blur="confirmRename(file)"
              @keyup.enter="confirmRename(file)"
              @click.stop
              autofocus
            />
            <span v-else class="file-name" :title="file.name">{{ file.name }}</span>
            <button class="delete-file-btn" @click.stop="closeGraph(file.filename)" title="Close File">
              <X size="12" />
            </button>
          </div>
          <div v-if="files.length === 0" class="empty-state">
            {{ $t('network.noGraphs') }}
          </div>
        </div>
      </div>

      <div class="graph-main-area">
        <!-- Graph Canvas -->
        <div class="graph-container glass-panel">
          <div class="graph-toolbar">
            <button class="tool-btn" @click="isSidebarVisible = !isSidebarVisible" :title="isSidebarVisible ? 'Hide Sidebar' : 'Show Sidebar'">
              <PanelLeftClose v-if="isSidebarVisible" size="16" />
              <PanelLeftOpen v-else size="16" />
            </button>
            <div class="divider"></div>
            <button class="tool-btn" @click="addNode" :title="$t('network.addNode')">
              <Plus size="16" /> {{ $t('network.addNode') }}
            </button>
            <div class="divider"></div>
            <button class="tool-btn" @click="addGroup" :title="$t('network.addGroup')">
              <Square size="16" /> {{ $t('network.addGroup') }}
            </button>
            <div class="divider"></div>
            <button class="tool-btn" :class="{ 'active': snapToGrid }" @click="snapToGrid = !snapToGrid" title="Toggle Grid Snap">
              <Grid size="16" :color="snapToGrid ? 'var(--accent-orange)' : 'currentColor'" /> Snap
            </button>
            <div class="divider"></div>
            <span class="toolbar-hint">
              <Link size="14" /> {{ $t('network.toolbarHint') }}
            </span>
            
            <div style="margin-left: auto;">
              <button class="save-btn" :class="{ 'btn-success': saveSuccess }" @click="exportGraph">
                <Check v-if="saveSuccess" size="16" />
                <Download v-else size="16" />
                <span>{{ saveSuccess ? $t('network.saved') : $t('network.exportDisk') }}</span>
              </button>
            </div>
          </div>

          <div class="canvas-wrapper" tabindex="0" @keydown="onKeyDown">
            <VueFlow 
              v-model:nodes="nodes" 
              v-model:edges="edges"
              :default-zoom="1"
              :min-zoom="0.2"
              :max-zoom="4"
              :pan-on-drag="[1, 2]"
              :selection-on-drag="true"
              :snap-to-grid="snapToGrid"
              :snap-grid="[20, 20]"
            >
              <Background pattern-color="#333" :gap="20" />
              <Controls />
              
              <template #node-custom="props">
                <NodeResizer :min-width="150" :min-height="40" :is-visible="selectedNode?.id === props.id" />
                <div class="custom-node" :class="{ selected: selectedNode?.id === props.id }" :style="{ borderColor: props.data.color, boxShadow: `0 0 10px ${props.data.color}40` }">
                  <!-- Stacked handles for omni-directional linking -->
                  <Handle type="target" :position="Position.Top" id="top-t" class="custom-handle" />
                  <Handle type="source" :position="Position.Top" id="top-s" class="custom-handle" />
                  
                  <Handle type="target" :position="Position.Bottom" id="bottom-t" class="custom-handle" />
                  <Handle type="source" :position="Position.Bottom" id="bottom-s" class="custom-handle" />
                  
                  <Handle type="target" :position="Position.Left" id="left-t" class="custom-handle" />
                  <Handle type="source" :position="Position.Left" id="left-s" class="custom-handle" />
                  
                  <Handle type="target" :position="Position.Right" id="right-t" class="custom-handle" />
                  <Handle type="source" :position="Position.Right" id="right-s" class="custom-handle" />
                  
                  <div class="node-content">
                    <div class="node-icon">
                      <component :is="availableIcons[props.data.iconName]" size="16" :color="props.data.color" />
                    </div>
                    <div 
                      v-if="editingNodeId !== props.id"
                      class="node-label" 
                      @dblclick="editingNodeId = props.id"
                    >
                      {{ props.data.label }}
                    </div>
                    <input 
                      v-else
                      v-model="props.data.label" 
                      class="node-input" 
                      placeholder="Name..."
                      autofocus
                      @blur="editingNodeId = null"
                      @keyup.enter="editingNodeId = null"
                    />
                  </div>
                </div>
              </template>

              <template #node-group="props">
                <NodeResizer :min-width="200" :min-height="100" :is-visible="selectedNode?.id === props.id" />
                <div class="group-node" :class="{ selected: selectedNode?.id === props.id }" :style="{ borderColor: props.data.color, backgroundColor: `${props.data.color}15` }">
                  <div class="group-header">
                    <button class="minimize-btn" :title="$t('network.group')">
                      <Minus size="12" />
                    </button>
                    <input 
                      v-model="props.data.label" 
                      class="group-title-input" 
                      :placeholder="$t('network.untitledGroup')"
                    />
                  </div>
                </div>
              </template>
            </VueFlow>
          </div>

          <!-- Edge Context Menu -->
          <div 
            v-if="contextMenu.visible" 
            class="edge-context-menu" 
            :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
          >
            <input 
              type="text" 
              class="edge-label-input" 
              v-model="contextMenu.label" 
              @input="updateSelectedEdgeLabel($event.target.value)"
              :placeholder="$t('network.relLabel')"
            />
            <div class="edge-styles">
              <button class="style-btn" @click="changeEdgeStyle('uni')" title="Unidirectional">
                <ArrowRight size="16" />
              </button>
              <button class="style-btn" @click="changeEdgeStyle('bi')" title="Bidirectional">
                <ArrowLeftRight size="16" />
              </button>
              <button class="style-btn" @click="changeEdgeStyle('none')" title="No Direction">
                <Minus size="16" />
              </button>
              <button class="style-btn" @click="changeEdgeStyle('animated')" title="Animated Flow">
                <Activity size="16" />
              </button>
              <div style="width: 1px; height: 20px; background: var(--border-color); margin: 0 4px;"></div>
              <button class="style-btn" @click="changeEdgePathType('default')" title="Flexible Curve">
                <Spline size="16" />
              </button>
              <button class="style-btn" @click="changeEdgePathType('straight')" title="Straight Line">
                <Slash size="16" />
              </button>
              <button class="style-btn" @click="changeEdgePathType('smoothstep')" title="Right Angles (Step)">
                <CornerDownRight size="16" />
              </button>
            </div>
            <div class="color-presets">
              <button class="color-btn" style="background: #3B82F6;" @click="changeSelectedEdgeColor('#3B82F6')"></button>
              <button class="color-btn" style="background: #10B981;" @click="changeSelectedEdgeColor('#10B981')"></button>
              <button class="color-btn" style="background: #F59E0B;" @click="changeSelectedEdgeColor('#F59E0B')"></button>
              <button class="color-btn" style="background: #EF4444;" @click="changeSelectedEdgeColor('#EF4444')"></button>
              <button class="color-btn" style="background: #8B5CF6;" @click="changeSelectedEdgeColor('#8B5CF6')"></button>
              <button class="color-btn" style="background: #FF7700;" @click="changeSelectedEdgeColor('#FF7700')"></button>
            </div>
            <div class="custom-color-wrapper">
              <span class="text-muted text-sm mr-2" style="font-size: 0.75rem;">{{ $t('network.custom') }}</span>
              <input 
                type="color" 
                class="custom-color-picker" 
                @input="changeSelectedEdgeColor($event.target.value)"
              />
            </div>
          </div>
        </div>

        <!-- Node Details Sidebar (Markdown Editor) -->
        <div class="node-sidebar glass-panel" v-if="selectedNode">
          <div class="sidebar-header">
            <h3>{{ $t('network.entityDetails') }}</h3>
            <button class="icon-btn" @click="selectedNode = null"><X size="18" /></button>
          </div>
          
          <div class="sidebar-content">
            <div class="field-group" v-if="selectedNode.type !== 'group'">
              <label>{{ $t('network.icon') }}</label>
              <div class="icon-selector">
                <button 
                  v-for="(_, iconName) in availableIcons" 
                  :key="iconName"
                  class="icon-picker-btn"
                  :class="{ active: selectedNode.data.iconName === iconName }"
                  @click="selectedNode.data.iconName = iconName"
                  :title="iconName"
                >
                  <component :is="availableIcons[iconName]" size="16" />
                </button>
              </div>
            </div>

            <div class="field-group">
              <label>{{ $t('network.color') }}</label>
              <div class="color-presets" style="margin-top: 4px;">
                <button class="color-btn" style="background: #3B82F6;" @click="selectedNode.data.color = '#3B82F6'"></button>
                <button class="color-btn" style="background: #10B981;" @click="selectedNode.data.color = '#10B981'"></button>
                <button class="color-btn" style="background: #F59E0B;" @click="selectedNode.data.color = '#F59E0B'"></button>
                <button class="color-btn" style="background: #EF4444;" @click="selectedNode.data.color = '#EF4444'"></button>
                <button class="color-btn" style="background: #8B5CF6;" @click="selectedNode.data.color = '#8B5CF6'"></button>
                <button class="color-btn" style="background: #FF7700;" @click="selectedNode.data.color = '#FF7700'"></button>
                <button class="color-btn" style="background: #6B7280;" @click="selectedNode.data.color = '#6B7280'"></button>
                <button class="color-btn" style="background: #EC4899;" @click="selectedNode.data.color = '#EC4899'"></button>
                <button class="color-btn" style="background: #ffffff;" @click="selectedNode.data.color = '#ffffff'"></button>
              </div>
            </div>

            <div class="field-group">
              <label>{{ $t('network.nameId') }}</label>
              <input type="text" v-model="selectedNode.data.label" class="styled-input" spellcheck="true" />
            </div>

            <div class="field-group flex-1 flex-col" style="min-height: 0;">
              <div class="md-header">
                <label>{{ $t('network.detailedNotes') }}</label>
              </div>
              
              <div class="md-split-container">
                <textarea 
                  v-model="selectedNode.data.notes" 
                  class="md-editor custom-scrollbar" 
                  :placeholder="$t('network.notesPlaceholder')"
                  spellcheck="true"
                ></textarea>
                
                <div 
                  class="md-preview custom-scrollbar markdown-body"
                  v-html="selectedNode.data.notes ? marked(selectedNode.data.notes) : `<em class='text-muted'>${$t('network.noNotes')}</em>`"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content glass-panel">
        <div class="modal-header">
          <Trash2 size="24" class="text-red" />
          <h3>{{ $t('network.deleteConfirmTitle') }}</h3>
        </div>
        <div class="modal-body">
          <p>{{ $t('network.deleteConfirmMessage') }}</p>
        </div>
        <div class="modal-actions">
          <button class="cancel-btn" @click="showDeleteModal = false">{{ $t('network.cancel') }}</button>
          <button class="delete-btn" @click="confirmDeleteGraph">{{ $t('network.delete') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.header-section { margin-bottom: 16px; }
.page-title { font-size: 2rem; margin-bottom: 8px; }
.page-subtitle { color: var(--text-muted); font-size: 0.95rem; }

.graph-layout {
  display: flex;
  flex: 1;
  gap: 16px;
  overflow: hidden;
}

/* File Explorer */
.file-explorer {
  width: 250px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);

  overflow: hidden;
}

.explorer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--overlay-8);
  border-bottom: 1px solid var(--border-color);
}
.explorer-header span { font-size: 0.95rem; }
.text-orange { color: var(--accent-orange); }

.icon-btn {
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-muted);

  padding: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover {
  color: var(--accent-orange);
  border-color: var(--accent-orange);
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;

  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.2s;
  margin-bottom: 4px;
}
.file-item:hover {
  background: var(--overlay-8);
  color: var(--text-main);
}
.file-item.active {
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--accent-orange);
  border: 1px solid rgba(var(--accent-rgb), 0.2);
}
.file-icon { opacity: 0.7; }

.file-name {
  flex: 1;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rename-input {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--accent-orange);
  color: var(--text-main);
  padding: 2px 4px;

  outline: none;
  font-size: 0.85rem;
  width: 100%;
}

.delete-file-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;

  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
}
.file-item:hover .delete-file-btn { opacity: 1; }
.delete-file-btn:hover { color: var(--accent-red); background: rgba(239, 68, 68, 0.2); }

.empty-state {
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* Save Button */
.save-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(var(--accent-rgb), 0.1);
  border: 1px solid var(--accent-orange);
  color: var(--accent-orange);
  padding: 6px 14px;

  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.save-btn:hover:not(:disabled) {
  background: var(--accent-orange);
  color: var(--bg-dark);
}
.save-btn.btn-success {
  background: var(--overlay-8);
  border-color: var(--accent-green);
  color: var(--accent-green);
}

.graph-main-area {
  display: flex;
  flex: 1;
  gap: 16px;
  overflow: hidden;
}

.graph-container {
  flex: 1;
  display: flex;
  flex-direction: column;

  overflow: hidden;
  border: 1px solid var(--border-color);
}

.graph-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--overlay-8);
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--overlay-8);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  padding: 8px 12px;

  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  width: 400px;
  max-width: 90vw;
  padding: 24px;

  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: slideUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: 1.25rem;
  margin: 0;
  color: var(--text-main);
}

.text-red {
  color: var(--accent-red);
}

.modal-body p {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.cancel-btn {
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 8px 16px;

  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: var(--overlay-10);
}

.delete-btn {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid var(--accent-red);
  color: var(--accent-red);
  padding: 8px 16px;

  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s;
}

.delete-btn:hover {
  background: var(--accent-red);
  color: var(--bg-dark);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.tool-btn:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
}

.divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 8px;
}

.toolbar-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-left: 8px;
}

.color-btn {
  width: 20px;
  height: 20px;

  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.color-btn:hover {
  transform: scale(1.2);
  border-color: var(--text-main);
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  background: var(--bg-dark);
  outline: none;
}

/* Custom Node Styles */
.custom-node {
  background: var(--bg-panel);
  border: 2px solid;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  border-radius: 6px;
  backdrop-filter: blur(4px);
  min-width: 150px;
  transition: box-shadow 0.2s ease;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* Group Node Styles */
.group-node {
  width: 100%;
  height: 100%;
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
}

.group-node.selected {
  border-style: solid;
  border-color: var(--accent-orange) !important;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.group-title-input {
  background: transparent;
  border: none;
  color: var(--text-main);
  font-weight: 600;
  font-size: 0.85rem;
  width: 100%;
  outline: none;
}

.minimize-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.custom-node.selected {
  border-color: var(--accent-orange) !important;

}

.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-input {
  background: var(--bg-panel);
  border: 1px solid var(--accent-orange);
  color: var(--text-main);
  font-size: 0.9rem;
  font-weight: 500;
  width: 100%;
  outline: none;
  padding: 2px 4px;

}

.node-label {
  color: var(--text-main);
  font-size: 0.9rem;
  font-weight: 500;
  width: 100%;
  cursor: pointer;
  padding: 3px 5px;
  word-break: break-word;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 20;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edge-context-menu {
  position: fixed;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 8px 12px;

  gap: 12px;

  z-index: 1000;
  transform: translate(-50%, -100%);
  margin-top: -10px;
}

.color-presets, .edge-styles {
  display: flex;
  gap: 8px;
}

.edge-styles {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.style-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-main);

  cursor: pointer;
  transition: all 0.2s ease;
}
.style-btn:hover {
  background: var(--overlay-10);
  border-color: var(--accent-orange);
  color: var(--accent-orange);
}

.edge-label-input {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 8px;

  font-size: 0.85rem;
  width: 100%;
  outline: none;
}
.edge-label-input:focus {
  border-color: var(--accent-orange);
}

.custom-color-wrapper {
  display: flex;
  align-items: center;
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
}

.custom-color-picker {
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;

  background: transparent;
  cursor: pointer;
}

.custom-color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.custom-color-picker::-webkit-color-swatch {
  border: 1px solid var(--border-color);

}

/* Sidebar Styles */
.node-sidebar {
  width: 350px;

  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--overlay-8);
  border-bottom: 1px solid var(--border-color);
}
.sidebar-header h3 { font-size: 1.1rem; font-weight: 600; margin: 0; }

.sidebar-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field-group { display: flex; flex-direction: column; gap: 8px; }
.field-group label { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; }
.styled-input {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 10px 12px;

  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
}
.styled-input:focus { border-color: var(--accent-orange); }

.flex-1 { flex: 1; }
.flex-col { display: flex; flex-direction: column; }

.md-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.md-split-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.md-editor {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  color: var(--text-main);
  padding: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  resize: none;
  outline: none;
  min-height: 100px;
}
.md-editor:focus { border-color: var(--accent-orange); }

.md-preview {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  padding: 12px;
  color: var(--text-main);
  font-size: 0.9rem;
  line-height: 1.6;
  overflow-y: auto;
  min-height: 100px;
}

/* Markdown basic styling */
:deep(.markdown-body h1), :deep(.markdown-body h2), :deep(.markdown-body h3) { margin-top: 0; margin-bottom: 8px; color: var(--text-main); }
:deep(.markdown-body p) { margin-top: 0; margin-bottom: 12px; }
:deep(.markdown-body a) { color: var(--accent-orange); text-decoration: none; }
:deep(.markdown-body a:hover) { text-decoration: underline; }
:deep(.markdown-body code) { background: var(--overlay-10); padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 0.85rem; }
:deep(.markdown-body pre) { background: var(--bg-panel); padding: 12px; border-radius: 8px; overflow-x: auto; margin-bottom: 12px; }
:deep(.markdown-body ul), :deep(.markdown-body ol) { margin-top: 0; padding-left: 20px; }

/* Vue Flow Overrides */
:deep(.vue-flow__handle) {
  width: 10px; height: 10px; background: var(--accent-orange);
  border: 2px solid var(--bg-dark); opacity: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

/* Force perfectly overlapping handles to prevent visual glitching */
:deep(.vue-flow__handle-top) { left: 50% !important; transform: translate(-50%, -50%) !important; }
:deep(.vue-flow__handle-bottom) { left: 50% !important; transform: translate(-50%, 50%) !important; }
:deep(.vue-flow__handle-left) { top: 50% !important; transform: translate(-50%, -50%) !important; }
:deep(.vue-flow__handle-right) { top: 50% !important; transform: translate(50%, -50%) !important; }

:deep(.vue-flow__node:hover .vue-flow__handle), :deep(.vue-flow__node.selected .vue-flow__handle) { opacity: 1; }
:deep(.vue-flow__handle:hover) { transform: scale(1.5); }
:deep(.vue-flow__edge-path) { stroke: var(--accent-orange); stroke-width: 2; transition: stroke 0.2s ease, stroke-width 0.2s ease; }
:deep(.vue-flow__edge.selected .vue-flow__edge-path) { stroke-width: 4; filter: drop-shadow(0 0 5px currentColor); }
</style>


<style scoped>
.icon-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: var(--overlay-8);

  border: 1px solid var(--border-color);
}
.icon-picker-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);

  padding: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-picker-btn:hover {
  background: var(--overlay-10);
  color: var(--text-main);
}
.icon-picker-btn.active {
  background: rgba(var(--accent-rgb), 0.2);
  color: var(--accent-orange);
  border-color: var(--accent-orange);
}
</style>
