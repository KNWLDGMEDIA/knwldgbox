<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Hash, Shield, DownloadCloud, Activity } from 'lucide-vue-next'
import html2pdf from 'html2pdf.js'

import TargetSearchBar from '../components/target/TargetSearchBar.vue'
import WhoisOverview from '../components/target/WhoisOverview.vue'
import UrlscanFootprint from '../components/target/UrlscanFootprint.vue'
import UrlscanInfrastructure from '../components/target/UrlscanInfrastructure.vue'
import UrlscanVerdicts from '../components/target/UrlscanVerdicts.vue'
import UrlscanMetrics from '../components/target/UrlscanMetrics.vue'
import HttpTransactionsTable from '../components/target/HttpTransactionsTable.vue'
import RequestDetailsModal from '../components/target/RequestDetailsModal.vue'
import DnsRecords from '../components/target/DnsRecords.vue'
import SslCertificate from '../components/target/SslCertificate.vue'
import SecurityHeaders from '../components/target/SecurityHeaders.vue'
import OpenPorts from '../components/target/OpenPorts.vue'
import CrawlRules from '../components/target/CrawlRules.vue'
import LinkedPages from '../components/target/LinkedPages.vue'
import PagesList from '../components/target/PagesList.vue'
import SubdomainsList from '../components/target/SubdomainsList.vue'
import TechStack from '../components/target/TechStack.vue'
import WaybackHistory from '../components/target/WaybackHistory.vue'
import ServerLocation from '../components/target/ServerLocation.vue'
import { MasonryWall } from '@yeger/vue-masonry-wall'

const { t } = useI18n()

const domain = ref('')
const isLoading = ref(false)
const isExporting = ref(false)
const route = useRoute()

watch(
  () => route.query.domain,
  (queryDomain) => {
    if (queryDomain) {
      if (domain.value !== queryDomain) {
        domain.value = queryDomain
        setTimeout(() => scanTarget(), 50)
      }
    }
  },
  { immediate: true }
)

const whoisData = ref(null)
const urlscanData = ref(null)
const dnsData = ref(null)
const sslData = ref(null)
const headersData = ref(null)
const portsData = ref(null)
const crawlData = ref(null)
const subdomainsData = ref(null)
const techData = ref(null)
const waybackData = ref(null)
const geoData = ref(null)
const errorMsg = ref(null)
const expandedRequest = ref(null)

const API_BASE = `http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api`

const masonryItems = computed(() => {
  const items = []

  if (urlscanData.value) {
    items.push({ id: 'UrlscanFootprint', component: UrlscanFootprint, props: { urlscan: urlscanData.value } })
    items.push({ id: 'UrlscanMetrics', component: UrlscanMetrics, props: { urlscan: urlscanData.value } })
    items.push({ id: 'UrlscanInfrastructure', component: UrlscanInfrastructure, props: { urlscan: urlscanData.value } })
    if (urlscanData.value?.detailed?.data?.requests?.length) {
      items.push({
        id: 'HttpTransactionsTable',
        component: HttpTransactionsTable,
        props: {
          requests: urlscanData.value.detailed.data.requests,
          onSelect: (req) => expandedRequest.value = req
        }
      })
    }
  }

  if (whoisData.value) {
    items.push({ id: 'WhoisOverview', component: WhoisOverview, props: { whois: whoisData.value } })
  }

  if (headersData.value) {
    items.push({ id: 'SecurityHeaders', component: SecurityHeaders, props: { headers: headersData.value } })
  }

  if (crawlData.value) {
    items.push({ id: 'CrawlRules', component: CrawlRules, props: { rules: crawlData.value.rules } })
    items.push({ id: 'LinkedPages', component: LinkedPages, props: { crawl: crawlData.value, domain: domain.value } })
    items.push({ id: 'PagesList', component: PagesList, props: { crawl: crawlData.value, domain: domain.value } })
  }

  if (techData.value && techData.value.length) {
    items.push({ id: 'TechStack', component: TechStack, props: { technologies: techData.value } })
  }

  if (geoData.value) {
    items.push({ id: 'ServerLocation', component: ServerLocation, props: { geo: geoData.value } })
  }

  if (subdomainsData.value && subdomainsData.value.length) {
    items.push({ id: 'SubdomainsList', component: SubdomainsList, props: { subdomains: subdomainsData.value, domain: domain.value } })
  }

  if (waybackData.value) {
    items.push({ id: 'WaybackHistory', component: WaybackHistory, props: { wayback: waybackData.value } })
  }

  if (sslData.value) {
    items.push({ id: 'SslCertificate', component: SslCertificate, props: { ssl: sslData.value } })
  }

  if (portsData.value) {
    items.push({ id: 'OpenPorts', component: OpenPorts, props: { ports: portsData.value } })
  }

  if (dnsData.value) {
    items.push({ id: 'DnsRecords', component: DnsRecords, props: { dns: dnsData.value } })
  }

  if (urlscanData.value?.detailed?.verdicts) {
    items.push({ id: 'UrlscanVerdicts', component: UrlscanVerdicts, props: { verdicts: urlscanData.value.detailed.verdicts } })
  }

  return items
})

async function scanTarget() {
  if (!domain.value.trim()) return

  isLoading.value = true
  errorMsg.value = null
  whoisData.value = null
  urlscanData.value = null
  dnsData.value = null
  sslData.value = null
  headersData.value = null
  portsData.value = null
  crawlData.value = null
  subdomainsData.value = null
  techData.value = null
  waybackData.value = null
  geoData.value = null

  const encodedDomain = encodeURIComponent(domain.value.trim())

  try {
    const [whoisRes, urlscanRes, dnsRes, sslRes, headersRes, portsRes, crawlRes, subRes, techRes, waybackRes, geoRes] = await Promise.allSettled([
      fetch(`${API_BASE}/whois?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/urlscan?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/dns?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/ssl?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/headers?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/ports?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/crawl?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/subdomains?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/technologies?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/wayback?domain=${encodedDomain}`).then(r => r.json()),
      fetch(`${API_BASE}/target/geolocation?domain=${encodedDomain}`).then(r => r.json())
    ])

    if (whoisRes.status === 'fulfilled') {
      if (whoisRes.value.status === 'success') {
        whoisData.value = whoisRes.value.data
      } else {
        errorMsg.value = whoisRes.value.message
      }
    } else {
      errorMsg.value = t('targetAnalysis.failedToFetchWhoisData')
    }

    if (urlscanRes.status === 'fulfilled' && urlscanRes.value.status === 'success') {
      urlscanData.value = urlscanRes.value.data
    }
    if (dnsRes.status === 'fulfilled' && dnsRes.value.status === 'success') {
      dnsData.value = dnsRes.value.data
    }
    if (sslRes.status === 'fulfilled' && sslRes.value.status === 'success') {
      sslData.value = sslRes.value.data
    }
    if (headersRes.status === 'fulfilled' && headersRes.value.status === 'success') {
      headersData.value = headersRes.value.data
    }
    if (portsRes.status === 'fulfilled' && portsRes.value.status === 'success') {
      portsData.value = portsRes.value.data
    }
    if (crawlRes.status === 'fulfilled' && crawlRes.value.status === 'success') {
      crawlData.value = crawlRes.value.data
    }
    if (subRes.status === 'fulfilled' && subRes.value.status === 'success') {
      subdomainsData.value = subRes.value.data
    }
    if (techRes.status === 'fulfilled' && techRes.value.status === 'success') {
      techData.value = techRes.value.data
    }
    if (waybackRes.status === 'fulfilled' && waybackRes.value.status === 'success') {
      waybackData.value = waybackRes.value.data
    }
    if (geoRes.status === 'fulfilled' && geoRes.value.status === 'success') {
      geoData.value = geoRes.value.data
    }

  } catch (err) {
    errorMsg.value = err.message
  } finally {
    isLoading.value = false
  }
}

async function exportToPdf() {
  if (isExporting.value) return
  isExporting.value = true

  const element = document.querySelector('.results-container')
  if (!element) {
    isExporting.value = false
    return
  }

  const opt = {
    margin:       10,
    filename:     `${domain.value || 'target'}-osint-report.pdf`,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#07090E' },
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
  <div class="target-page">
    <div class="content-wrapper">
      <div class="header-section">
        <div>
          <h1 class="page-title">{{ t('targetAnalysis.title') }}</h1>
          <p class="page-subtitle">{{ t('targetAnalysis.subtitle') }}</p>
        </div>
        <button
          v-if="whoisData || urlscanData || dnsData"
          class="export-btn"
          @click="exportToPdf"
          :disabled="isExporting"
        >
          <component :is="isExporting ? Activity : DownloadCloud" size="16" />
          {{ isExporting ? t('targetAnalysis.generatingPdf') : t('targetAnalysis.exportPdf') }}
        </button>
      </div>

      <TargetSearchBar
        v-model="domain"
        :is-loading="isLoading"
        @submit="scanTarget"
      />

      <div v-if="errorMsg" class="error-banner glass-panel">
        <Shield size="16" />
        <span>{{ errorMsg }}</span>
      </div>

      <div v-if="(whoisData || urlscanData || dnsData || crawlData || subdomainsData || techData || waybackData) && !isLoading" class="results-container">
        <masonry-wall :items="masonryItems" :ssr-columns="1" :column-width="350" :gap="20">
          <template #default="{ item }">
            <component :is="item.component" v-bind="item.props" />
          </template>
        </masonry-wall>
      </div>

      <div v-else-if="!isLoading && !errorMsg" class="empty-state glass-panel">
        <Hash size="48" class="empty-icon" />
        <h3>{{ t('targetAnalysis.noTargetAnalyzed') }}</h3>
        <p>{{ t('targetAnalysis.noTargetMessage') }}</p>
      </div>

      <RequestDetailsModal
        v-if="expandedRequest"
        :request="expandedRequest"
        @close="expandedRequest = null"
      />
    </div>
  </div>
</template>

<style scoped>
.target-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding-right: 16px;
}

.content-wrapper {
  max-width: 100%;
  padding: 0 10px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

.header-section {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

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

.page-title { font-size: 2rem; margin-bottom: 8px; }
.page-subtitle { color: var(--text-muted); font-size: 0.95rem; }

.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--accent-red);

  margin-bottom: 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;

}

.empty-icon {
  color: var(--border-color);
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state h3 { font-size: 1.2rem; margin-bottom: 8px; color: var(--text-main); }
.empty-state p { color: var(--text-muted); font-size: 0.95rem; max-width: 400px; }

:deep(.result-card) {
  padding: 20px;

  display: flex;
  flex-direction: column;
}

:deep(.card-header) {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}
:deep(.card-header h3) { font-size: 1.1rem; font-weight: 600; margin: 0; }

:deep(.card-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

:deep(.data-row) {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
:deep(.data-row.stack) {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

:deep(.label) {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-weight: 500;
}

:deep(.value) {
  font-size: 0.95rem;
  color: var(--text-main);
  font-weight: 500;
}

:deep(.highlight) {
  color: var(--accent-purple);
  font-weight: 700;
  font-size: 1.1rem;
}

:deep(.text-purple) { color: var(--accent-purple); }
:deep(.text-orange) { color: var(--accent-orange); }
:deep(.text-red) { color: var(--accent-red); }
:deep(.text-green) { color: var(--accent-green); }
:deep(.text-blue) { color: #3B82F6; }
</style>
