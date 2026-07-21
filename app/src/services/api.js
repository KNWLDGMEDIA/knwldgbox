const API_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api`
const WS_BASE = `ws://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/ws`

export const apiService = {
  async saveSettings(settings) {
    const response = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    })
    return await response.json()
  },

  async requestTelegramCode() {
    const response = await fetch(`${API_BASE}/telegram/auth/send_code`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error("Failed to request code")
    return await response.json()
  },

  async verifyTelegramCode(code) {
    const response = await fetch(`${API_BASE}/telegram/auth/verify_code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Verification failed')
    }
    return await response.json()
  },

  createTelegramWebSocket() {
    return new WebSocket(`${WS_BASE}/telegram`)
  },

  createSherlockWebSocket() {
    return new WebSocket(`${WS_BASE}/sherlock`)
  },

  createTikTokWebSocket() {
    return new WebSocket(`${WS_BASE}/tiktok`)
  },

  createMaigretWebSocket() {
    return new WebSocket(`${WS_BASE}/maigret`)
  },

  createHoleheWebSocket() {
    return new WebSocket(`${WS_BASE}/holehe`)
  },

  createDownloaderWebSocket() {
    return new WebSocket(`${WS_BASE}/downloader`)
  },

  async listDownloads() {
    const response = await fetch(`${API_BASE}/downloads/list`)
    return await response.json()
  },

  async openDownloadsDirectory() {
    const response = await fetch(`${API_BASE}/downloads/open`, {
      method: 'POST'
    })
    return await response.json()
  },

  async listGraphs() {
    const response = await fetch(`${API_BASE}/graphs`)
    return await response.json()
  },

  async loadGraph(filename) {
    const response = await fetch(`${API_BASE}/graphs/${encodeURIComponent(filename)}`)
    if (!response.ok) throw new Error("Failed to load graph")
    return await response.json()
  },

  async saveGraph(filename, data) {
    const response = await fetch(`${API_BASE}/graphs/${encodeURIComponent(filename)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error("Failed to save graph")
    return await response.json()
  },

  async deleteGraph(filename) {
    const response = await fetch(`${API_BASE}/graphs/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    })
    if (!response.ok) throw new Error("Failed to delete graph")
    return await response.json()
  },

  async renameGraph(filename, newName) {
    const response = await fetch(`${API_BASE}/graphs/${encodeURIComponent(filename)}/rename`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ newName })
    })
    if (!response.ok) throw new Error("Failed to rename graph")
    return await response.json()
  }
}
