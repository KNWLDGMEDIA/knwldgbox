<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  GlobeLock,
  Users,
  ShieldAlert,
  ListTree,
  ExternalLink,
  Link as LinkIcon,
  Search,
  Target,
  Download,
  Archive,
  Map as MapIcon,
  Wrench,
  Settings,
  Activity,
  MessageSquare,
  Aperture,
  ChevronDown
} from 'lucide-vue-next'
import MonitoringMap from '../components/MonitoringMap.vue'
import { globalMapLocations } from '../store.js'

const router = useRouter()
const searchQuery = ref('')
const searchType = ref('domain')
const backendStatus = ref('checking')

const stats = ref({
  monitoringBlocks: 0,
  leakBlocks: 0,
  savedDorks: 0,
  savedGraphs: 0,
})

const tools = [
  { nameKey: 'sidebar.monitoring', descKey: 'dashboard.toolsDesc.monitoring', icon: ListTree, route: '/monitoring', color: '#FF7700' },
  { nameKey: 'sidebar.socialForensics', descKey: 'dashboard.toolsDesc.social', icon: Users, route: '/social', color: '#3B82F6' },
  { nameKey: 'sidebar.targetAnalysis', descKey: 'dashboard.toolsDesc.target', icon: Target, route: '/target', color: '#8B5CF6' },
  { nameKey: 'sidebar.networkGraph', descKey: 'dashboard.toolsDesc.network', icon: GlobeLock, route: '/network', color: '#10B981' },
  { nameKey: 'sidebar.dataLeaks', descKey: 'dashboard.toolsDesc.leaks', icon: ShieldAlert, route: '/leaks', color: '#EF4444' },
  { nameKey: 'sidebar.dorkBuilder', descKey: 'dashboard.toolsDesc.dorks', icon: Search, route: '/dorks', color: '#A855F7' },
  { nameKey: 'sidebar.mediaDownloaders', descKey: 'dashboard.toolsDesc.media', icon: Download, route: '/downloaders', color: '#F59E0B' },
  { nameKey: 'sidebar.archives', descKey: 'dashboard.toolsDesc.archives', icon: Archive, route: '/archives', color: '#6366F1' },
  { nameKey: 'sidebar.osintMap', descKey: 'dashboard.toolsDesc.osintMap', icon: MapIcon, route: '/osint-map', color: '#EC4899' },
  { nameKey: 'sidebar.knwldgTools', descKey: 'dashboard.toolsDesc.tools', icon: Wrench, route: '/tools', color: '#14B8A6' },
  { nameKey: 'sidebar.imageForensics', descKey: 'Analyze image metadata and manipulation', icon: Aperture, route: '/forensics', color: '#D946EF' },
  { nameKey: 'sidebar.aiChatbot', descKey: 'dashboard.toolsDesc.aiChatbot', icon: MessageSquare, route: '/ai-chat', color: '#0EA5E9' },
  { nameKey: 'sidebar.settings', descKey: 'dashboard.toolsDesc.settings', icon: Settings, route: '/settings', color: '#64748B' },
]

const usefulLinks = [
  { title: 'Epieos', url: 'https://epieos.com/', desc: 'Email & Google OSINT', category: 'People' },
  { title: 'WhatsMyName', url: 'https://whatsmyname.app/', desc: 'Username enumeration', category: 'People' },
  { title: 'PimEyes', url: 'https://pimeyes.com/', desc: 'Facial recognition', category: 'People' },
  { title: 'Truecaller', url: 'https://www.truecaller.com/', desc: 'Phone search', category: 'People' },
  { title: 'DeHashed', url: 'https://dehashed.com/', desc: 'Data leaks', category: 'Leaks' },
  { title: 'HaveIBeenPwned', url: 'https://haveibeenpwned.com/', desc: 'Email breach check', category: 'Leaks' },
  { title: 'Shodan', url: 'https://www.shodan.io/', desc: 'IoT search engine', category: 'Network' },
  { title: 'VirusTotal', url: 'https://www.virustotal.com/', desc: 'File analysis', category: 'Network' },
  { title: 'Censys', url: 'https://search.censys.io/', desc: 'Attack surface', category: 'Network' },
  { title: 'SecurityTrails', url: 'https://securitytrails.com/', desc: 'DNS intelligence', category: 'Network' },
  { title: 'GreyNoise', url: 'https://www.greynoise.io/', desc: 'Internet noise', category: 'Network' },
  { title: 'BuiltWith', url: 'https://builtwith.com/', desc: 'Tech profiler', category: 'Network' },
  { title: 'CRT.sh', url: 'https://crt.sh/', desc: 'Certificate logs', category: 'Network' },
  { title: 'Liveuamap', url: 'https://liveuamap.com/', desc: 'Awareness map', category: 'Geo' },
  { title: 'NASA FIRMS', url: 'https://firms.modaps.eosdis.nasa.gov/', desc: 'Fire mapping', category: 'Geo' },
  { title: 'Flightradar24', url: 'https://www.flightradar24.com/', desc: 'Flight tracking', category: 'Tracking' },
  { title: 'ADS-B Exchange', url: 'https://globe.adsbexchange.com/', desc: 'Flight data', category: 'Tracking' },
  { title: 'MarineTraffic', url: 'https://www.marinetraffic.com/', desc: 'Ship tracking', category: 'Tracking' },
  { title: 'TinEye', url: 'https://tineye.com/', desc: 'Reverse image', category: 'Media' },
  { title: 'Breadcrumbs', url: 'https://www.breadcrumbs.app/', desc: 'Crypto tracing', category: 'Crypto' },
  { title: 'Blockchain.com', url: 'https://www.blockchain.com/explorer', desc: 'Blockchain explorer', category: 'Crypto' },
]

const groupedLinks = computed(() => {
  const groups = {}
  usefulLinks.forEach(link => {
    if (!groups[link.category]) groups[link.category] = []
    groups[link.category].push(link)
  })
  return groups
})

const activeCategory = ref(usefulLinks[0].category)

const recentGraphs = ref([])

onMounted(async () => {
  loadStats()
  await loadGraphsData()
  checkBackendHealth()
})

function loadStats() {
  try {
    const monitoring = JSON.parse(localStorage.getItem('knwldg_monitoring_blocks') || '[]')
    stats.value.monitoringBlocks = monitoring.length

    const leaks = JSON.parse(localStorage.getItem('knwldg_dataleaks_blocks') || '[]')
    stats.value.leakBlocks = leaks.length

    const dorks = JSON.parse(localStorage.getItem('knwldg_saved_dorks') || '[]')
    stats.value.savedDorks = dorks.length
  } catch {
    // localStorage unavailable
  }
}

async function loadGraphsData() {
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs`)
    if (res.ok) {
      const data = await res.json()
      const graphs = data.graphs || []
      recentGraphs.value = graphs.slice(0, 5)
      
      stats.value.savedGraphs = graphs.length
    }
  } catch (e) {
    console.error("Failed to load graphs data", e)
  }
}

async function checkBackendHealth() {
  try {
    const response = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/graphs`, { method: 'GET' })
    backendStatus.value = response.ok ? 'online' : 'error'
  } catch {
    backendStatus.value = 'offline'
  }
}

function navigateTo(route) {
  router.push(route)
}

function handleSearch() {
  if (!searchQuery.value.trim()) return
  const q = searchQuery.value.trim()
  if (searchType.value === 'domain') {
    router.push({ path: '/target', query: { domain: q } })
  } else {
    router.push({ path: '/social', query: { tab: searchType.value, query: q } })
  }
}

function getFaviconUrl(link) {
  try {
    const domain = new URL(link.url).hostname
    return `https://icon.horse/icon/${domain}`
  } catch {
    return ''
  }
}
</script>

<template>
  <div class="dashboard">
    <div class="header-section">
      <h1 class="page-title">{{ $t('dashboard.title') }}</h1>
      <p class="page-subtitle">{{ $t('dashboard.subtitle') }}</p>
    </div>

    <div class="quick-search glass-panel">
      <Search size="20" class="search-icon" />
      
      <div class="search-type-wrapper">
        <select v-model="searchType" class="search-type-select">
          <option value="domain">{{ $t('dashboard.searchTypeDomain') }}</option>
          <option value="sherlock">{{ $t('dashboard.searchTypeSherlock') }}</option>
          <option value="maigret">{{ $t('dashboard.searchTypeMaigret') }}</option>
          <option value="ghunt">{{ $t('dashboard.searchTypeGHunt') }}</option>
        </select>
        <ChevronDown size="14" class="dropdown-icon" />
      </div>
      <div class="divider"></div>
      
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="searchType === 'domain' ? $t('dashboard.searchPlaceholder') : searchType === 'sherlock' ? $t('dashboard.searchPlaceholderSherlock') : searchType === 'maigret' ? $t('dashboard.searchPlaceholderMaigret') : $t('dashboard.searchPlaceholderGHunt')"
        @keyup.enter="handleSearch"
        class="search-input"
      />
    </div>

    <div class="quick-tools">
      <div
        v-for="(tool, index) in tools"
        :key="index"
        class="tool-card glass-panel"
        @click="navigateTo(tool.route)"
      >
        <div class="tool-icon" :style="{ background: tool.color + '15' }">
          <component :is="tool.icon" size="24" :style="{ color: tool.color }" />
        </div>
        <div class="tool-info">
          <h3>{{ $t(tool.nameKey) }}</h3>
          <p>{{ $t(tool.descKey) }}</p>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <div class="panel glass-panel">
        <div class="panel-header">
          <h2>{{ $t('dashboard.workspaceSummary') }}</h2>
          <div class="backend-status" :class="backendStatus">
            <Activity size="14" />
            <span>{{ backendStatus }}</span>
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-card" @click="navigateTo('/monitoring')">
            <span class="stat-value">{{ stats.monitoringBlocks }}</span>
            <span class="stat-label">{{ $t('dashboard.activeMonitors') }}</span>
          </div>
          <div class="stat-card" @click="navigateTo('/network')">
            <span class="stat-value">{{ stats.savedGraphs }}</span>
            <span class="stat-label">{{ $t('dashboard.savedGraphs') }}</span>
          </div>
          <div class="stat-card" @click="navigateTo('/dorks')">
            <span class="stat-value">{{ stats.savedDorks }}</span>
            <span class="stat-label">{{ $t('dashboard.savedDorks') }}</span>
          </div>
          <div class="stat-card" @click="navigateTo('/leaks')">
            <span class="stat-value">{{ stats.leakBlocks }}</span>
            <span class="stat-label">{{ $t('dashboard.leakTrackers') }}</span>
          </div>
        </div>
      </div>

      <div class="panel glass-panel" v-if="recentGraphs.length > 0">
        <div class="panel-header">
          <h2>{{ $t('dashboard.recentGraphs') }}</h2>
          <button class="view-all-btn" @click="navigateTo('/network')">{{ $t('dashboard.viewAll') }}</button>
        </div>
        <div class="recent-list">
          <div
            v-for="graph in recentGraphs"
            :key="graph.filename"
            class="recent-item"
            @click="navigateTo('/network')"
          >
            <GlobeLock size="16" class="recent-icon" />
            <div class="recent-info">
              <span class="recent-name">{{ graph.name }}</span>
              <span class="recent-meta">{{ graph.nodes_count || 0 }} {{ $t('dashboard.nodes') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Map Overview -->
    <div class="map-overview-section">
      <MonitoringMap :locations="globalMapLocations" :previewMode="true" />
    </div>

    <div class="links-section">
      <div class="panel glass-panel">
        <div class="panel-header">
          <h2><LinkIcon size="18" style="vertical-align: middle; margin-right: 8px;" /> {{ $t('dashboard.osintDirectory') }}</h2>
        </div>
        
        <div class="category-tabs">
          <button 
            v-for="(links, category) in groupedLinks" 
            :key="category"
            class="tab-btn"
            :class="{ active: activeCategory === category }"
            @click="activeCategory = category"
          >
            {{ $t('dashboard.categories.' + category.toLowerCase()) }}
          </button>
        </div>

        <div class="links-compact-grid">
          <a
            v-for="(link, idx) in groupedLinks[activeCategory]"
            :key="idx"
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="link-compact"
          >
            <div class="link-compact-icon">
              <img :src="getFaviconUrl(link)" alt="" @error="$event.target.style.display='none'" />
            </div>
            <div class="link-compact-info">
              <h3>{{ link.title }}</h3>
              <p>{{ link.desc }}</p>
            </div>
            <ExternalLink size="12" class="external-icon" />
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.header-section { margin-bottom: 24px; }
.page-title { font-size: 2rem; margin-bottom: 8px; }
.page-subtitle { color: var(--text-muted); font-size: 0.95rem; }

.quick-search {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  margin-bottom: 24px;
}

.search-icon { color: var(--text-muted); flex-shrink: 0; }

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 0.95rem;
  outline: none;
}

.search-input::placeholder { color: var(--text-muted); }

.search-type-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-type-select {
  background: transparent;
  color: var(--accent-orange);
  border: none;
  outline: none;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  padding-right: 20px;
}
.search-type-select option {
  background: var(--bg-panel);
  color: var(--text-main);
}
.dropdown-icon {
  position: absolute;
  right: 0;
  color: var(--accent-orange);
  pointer-events: none;
}
.divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 8px;
}

.quick-tools {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.tool-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: var(--transition);
}

.tool-card:hover {
  border-color: var(--border-color);
  transform: translateY(-2px);
}

.tool-icon {
  padding: 10px;

  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
}

.tool-card:hover .tool-icon { transform: scale(1.1); }

.tool-info h3 { font-size: 0.95rem; margin-bottom: 4px; }
.tool-info p { font-size: 0.75rem; color: var(--text-muted); line-height: 1.3; }

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.panel { padding: 20px; }

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h2 { font-size: 1.05rem; font-weight: 500; }

.backend-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  padding: 4px 10px;

  text-transform: capitalize;
}

.backend-status.checking { background: var(--overlay-10); color: var(--text-muted); }
.backend-status.online { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
.backend-status.offline { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }
.backend-status.error { background: rgba(var(--accent-rgb), 0.15); color: var(--accent-orange); }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);

  cursor: pointer;
  transition: var(--transition);
}

.stat-card:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--accent-orange);
  font-family: 'JetBrains Mono', monospace;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);

  cursor: pointer;
  transition: var(--transition);
}

.recent-item:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
}

.recent-icon { color: var(--accent-orange); flex-shrink: 0; }

.recent-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.recent-name {
  font-size: 0.85rem;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-meta {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.view-all-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 5px 10px;

  font-size: 0.7rem;
  cursor: pointer;
  transition: var(--transition);
}

.view-all-btn:hover {
  background: var(--overlay-10);
  color: var(--text-main);
}

@media (max-width: 1024px) {
  .content-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
  .quick-tools { grid-template-columns: 1fr; }
}

.map-overview-section {
  margin-top: 24px;
  height: 350px;
  position: relative;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.map-overview-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
}
.map-overview-section:hover :deep(.monitoring-map-container) {
  border-color: var(--accent-orange);
}

.links-section { margin-top: 24px; }

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab-btn {
  background: var(--overlay-8);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 6px 12px;

  font-size: 0.75rem;
  cursor: pointer;
  transition: var(--transition);
}

.tab-btn:hover {
  background: var(--overlay-10);
  color: var(--text-main);
}

.tab-btn.active {
  background: var(--overlay-10);
  border-color: var(--border-color);
  color: var(--text-main);
}

.links-compact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.link-compact {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--overlay-8);
  border: 1px solid var(--border-color);

  text-decoration: none;
  transition: all 0.2s ease;
}

.link-compact:hover {
  background: var(--overlay-10);
  border-color: var(--border-color);
  transform: translateY(-1px);
}

.link-compact-icon {
  width: 28px;
  height: 28px;
  background: var(--overlay-10);

  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--border-color);
}

.link-compact-icon img {
  width: 16px;
  height: 16px;
}

.link-compact-info {
  flex: 1;
  min-width: 0;
}

.link-compact-info h3 {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-main);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.link-compact-info p {
  margin: 0;
  font-size: 0.65rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.external-icon {
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.link-compact:hover .external-icon {
  opacity: 0.6;
}

@media (max-width: 768px) {
  .links-compact-grid {
    grid-template-columns: 1fr;
  }
}

</style>
