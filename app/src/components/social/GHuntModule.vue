<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, Loader2, Globe, User, Mail, Key, Calendar, Shield } from 'lucide-vue-next'
import SendToGraphButton from '../SendToGraphButton.vue'

const { t } = useI18n()

const username = ref('')
const isSearching = ref(false)
const progressText = ref('')
const ghuntData = ref(null)

const showAuthModal = ref(false)
const showConfigPrompt = ref(false)
const b64Token = ref('')
const isAuthenticating = ref(false)
const authError = ref('')

onMounted(async () => {
  try {
    const res = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/ghunt/status`)
    if (res.ok) {
      const data = await res.json()
      if (!data.authenticated) {
        showConfigPrompt.value = true
      }
    }
  } catch (e) {
    console.error("Failed to fetch GHunt status", e)
  }
})

const ghuntProfile = computed(() => {
  if (!ghuntData.value || !ghuntData.value.PROFILE_CONTAINER) return null
  return ghuntData.value.PROFILE_CONTAINER.profile
})

const ghuntCalendar = computed(() => {
  if (!ghuntData.value || !ghuntData.value.PROFILE_CONTAINER) return null
  return ghuntData.value.PROFILE_CONTAINER.calendar
})

async function fetchGHuntData() {
  if (!username.value.trim() || isSearching.value) return

  isSearching.value = true
  progressText.value = t('socialForensics.ghunt.initializing')
  ghuntData.value = null

  try {
    const response = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/ghunt/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: username.value })
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || t('socialForensics.ghunt.failedFetch'))
    }

    ghuntData.value = data.data
    progressText.value = t('socialForensics.ghunt.complete')
  } catch (error) {
    if (error.message === 'auth_required') {
      showAuthModal.value = true
      progressText.value = t('socialForensics.ghunt.errors.auth_required')
    } else if (error.message.startsWith('unknown:')) {
      progressText.value = `${t('socialForensics.ghunt.errorPrefix')} ${error.message.replace('unknown:', '').trim()}`
    } else {
      const translationKey = `socialForensics.ghunt.errors.${error.message}`
      const translatedMsg = t(translationKey)
      // Fallback to the raw error message if the translation key doesn't exist
      progressText.value = `${t('socialForensics.ghunt.errorPrefix')} ${translatedMsg === translationKey ? error.message : translatedMsg}`
    }
  } finally {
    isSearching.value = false
  }
}

function stopSearch() {
  if (isSearching.value) {
    isSearching.value = false
    progressText.value = t('socialForensics.ghunt.aborted')
  }
}

async function authenticateGHunt() {
  if (!b64Token.value.trim()) return
  
  isAuthenticating.value = true
  authError.value = ''
  
  try {
    const response = await fetch(`http://${window.location.hostname}:${import.meta.env.VITE_API_PORT || (import.meta.env.DEV ? 8000 : window.location.port) || 8000}/api/ghunt/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ b64_token: b64Token.value.trim() })
    })
    
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to authenticate')
    }
    
    showAuthModal.value = false
    b64Token.value = ''
    progressText.value = t('socialForensics.ghunt.authSuccess')
    
    // Automatically retry the search
    fetchGHuntData()
    
  } catch (err) {
    authError.value = err.message
  } finally {
    isAuthenticating.value = false
  }
}
</script>

<template>
  <div class="ghunt-module">
    <div class="auth-overlay" v-if="showConfigPrompt">
      <div class="auth-modal glass-panel" style="max-width: 400px;">
        <div class="auth-header">
          <h3><Key size="18" class="text-orange" style="display:inline; margin-right:8px; vertical-align:middle;" />{{ t('socialForensics.ghunt.configTitle') }}</h3>
        </div>
        <p class="auth-desc">{{ t('socialForensics.ghunt.configPrompt') }}</p>
        <div class="auth-actions" style="margin-top: 24px;">
          <button class="btn-cancel" @click="showConfigPrompt = false">{{ t('socialForensics.ghunt.configLater') }}</button>
          <button class="btn-primary" @click="showConfigPrompt = false; showAuthModal = true">
            {{ t('socialForensics.ghunt.configNow') }}
          </button>
        </div>
      </div>
    </div>
    <div class="auth-overlay" v-if="showAuthModal">
      <div class="auth-modal glass-panel">
        <div class="auth-header">
          <h3><Key size="18" class="text-orange" style="display:inline; margin-right:8px; vertical-align:middle;" />{{ t('socialForensics.ghunt.authTitle') }}</h3>
        </div>
        <p class="auth-desc" v-html="t('socialForensics.ghunt.authDesc')"></p>
        <div class="form-group">
          <input 
            type="text" 
            v-model="b64Token" 
            :placeholder="t('socialForensics.ghunt.b64Placeholder')" 
            class="code-input" 
          />
          <span class="text-error" v-if="authError">{{ authError }}</span>
        </div>
        <div class="auth-actions">
          <button class="btn-cancel" @click="showAuthModal = false" :disabled="isAuthenticating">{{ t('common.cancel') }}</button>
          <button class="btn-primary" @click="authenticateGHunt" :disabled="!b64Token || isAuthenticating">
            <Loader2 size="16" class="spin" v-if="isAuthenticating" />
            <Key size="16" v-else />
            {{ isAuthenticating ? t('socialForensics.ghunt.authenticating') : t('socialForensics.ghunt.authenticate') }}
          </button>
        </div>
      </div>
    </div>
    <div class="search-panel glass-panel">
      <div class="input-wrapper">
        <Mail class="icon-user" size="20" />
        <input
          v-model="username"
          type="text"
          :placeholder="t('socialForensics.ghunt.placeholder')"
          @keyup.enter="fetchGHuntData"
          :disabled="isSearching"
        />
        <button class="btn-search" @click="fetchGHuntData" v-if="!isSearching">
          <Search size="18" /> {{ t('socialForensics.ghunt.search') }}
        </button>
        <button class="btn-stop" @click="stopSearch" v-else>
          <Loader2 size="18" class="spin" /> {{ t('socialForensics.ghunt.abort') }}
        </button>
      </div>
    </div>
    <div class="progress-area" v-if="isSearching || ghuntData || progressText">
      <div class="progress-header">
        <div class="status-badge" :class="{ 'scanning': isSearching, 'done': !isSearching && ghuntData, 'error': progressText.includes('Error') }">
          <div class="pulse-dot" v-if="isSearching"></div>
          <span>{{ progressText || (isSearching ? t('socialForensics.ghunt.scanning') : t('socialForensics.ghunt.idle')) }}</span>
        </div>
      </div>
      <div class="progress-track" v-if="isSearching">
        <div class="progress-fill indeterminate"></div>
      </div>
    </div>
    <div class="ghunt-results" v-if="ghuntData && ghuntProfile">
      <div class="profile-card">
        <div class="profile-header">
          <div class="avatar-container">
            <img
              :src="ghuntProfile.profilePhotos?.PROFILE?.url"
              alt="Profile Photo"
              class="avatar"
              v-if="ghuntProfile.profilePhotos?.PROFILE?.url"
            />
            <div class="avatar-placeholder" v-else>
              <User size="36" />
            </div>
            <div class="default-badge" v-if="ghuntProfile.profilePhotos?.PROFILE?.isDefault">{{ t('socialForensics.ghunt.defaultBadge') }}</div>
          </div>
          <div class="profile-main-info">
            <h2>{{ ghuntProfile.names?.PROFILE?.fullname || t('socialForensics.ghunt.unknownName') }}</h2>
            <div class="info-row">
              <Mail size="15" class="info-icon accent" />
              <span>{{ ghuntProfile.emails?.ACCOUNT?.value || username }}</span>
              <SendToGraphButton
                small
                :label="ghuntProfile.emails?.ACCOUNT?.value || username"
                iconName="Mail"
                color="#EF4444"
                :notes="t('socialForensics.ghunt.emailFoundNotes')"
                class="inline-btn"
              />
            </div>
            <div class="info-row">
              <Key size="15" class="info-icon muted" />
              <span class="text-muted mono">{{ ghuntProfile.personId }}</span>
              <SendToGraphButton
                small
                :label="`Gaia ID: ${ghuntProfile.personId}`"
                iconName="Hash"
                color="#8B5CF6"
                :notes="t('socialForensics.ghunt.gaiaNotes')"
                class="inline-btn"
              />
            </div>
          </div>
        </div>
      </div>
      <div class="details-grid">
        <div class="detail-card">
          <div class="card-title">
            <User size="16" />
            <span>{{ t('socialForensics.ghunt.accountDetails') }}</span>
          </div>
          <div class="detail-rows">
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.userType') }}</span>
              <span class="dv">{{ ghuntProfile.profileInfos?.PROFILE?.userTypes?.join(', ') || t('socialForensics.ghunt.unknownName') }}</span>
            </div>
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.lastUpdated') }}</span>
              <span class="dv">{{ ghuntProfile.sourceIds?.PROFILE?.lastUpdated || t('socialForensics.ghunt.unknownName') }}</span>
            </div>
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.enterpriseUser') }}</span>
              <span class="dv" :class="{ 'text-green': ghuntProfile.extendedData?.gplusData?.isEntrepriseUser }">
                {{ ghuntProfile.extendedData?.gplusData?.isEntrepriseUser ? t('socialForensics.ghunt.yes') : t('socialForensics.ghunt.no') }}
              </span>
            </div>
          </div>
        </div>
        <div class="detail-card">
          <div class="card-title">
            <Globe size="16" />
            <span>{{ t('socialForensics.ghunt.activatedServices') }}</span>
          </div>
          <div class="services-list" v-if="ghuntProfile.inAppReachability?.PROFILE?.apps?.length">
            <span class="service-badge" v-for="app in ghuntProfile.inAppReachability.PROFILE.apps" :key="app">
              {{ app }}
            </span>
          </div>
          <p class="text-muted empty-card-text" v-else>{{ t('socialForensics.ghunt.noActivatedServices') }}</p>
        </div>
        <div class="detail-card">
          <div class="card-title">
            <Calendar size="16" />
            <span>{{ t('socialForensics.ghunt.calendarData') }}</span>
          </div>
          <div v-if="ghuntCalendar?.details" class="detail-rows">
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.publicCalendar') }}</span>
              <span class="dv text-green">{{ t('socialForensics.ghunt.yes') }}</span>
            </div>
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.timezone') }}</span>
              <span class="dv">{{ ghuntCalendar.details.time_zone }}</span>
            </div>
            <div class="detail-row">
              <span class="dl">{{ t('socialForensics.ghunt.eventsFound') }}</span>
              <span class="dv">{{ ghuntCalendar.events?.items?.length || 0 }}</span>
            </div>
          </div>
          <p class="text-muted empty-card-text" v-else>{{ t('socialForensics.ghunt.noPublicCalendar') }}</p>
        </div>
      </div>
    </div>
    <div class="empty-state" v-if="!isSearching && !ghuntData && !progressText">
      <div class="empty-icon-wrapper">
        <Search size="48" class="text-muted" />
      </div>
      <h3>{{ t('socialForensics.ghunt.readyTitle') }}</h3>
      <p>{{ t('socialForensics.ghunt.readyText') }}</p>
      <p class="text-muted" style="font-size: 0.8rem; margin-top: 8px;">{{ t('socialForensics.ghunt.poweredBy') }}</p>
    </div>
  </div>
</template>

<style scoped>
.ghunt-module {
  display: flex;
  flex-direction: column;
  flex: 1;
}

/* ── Search Panel ─────────────────────────────── */
.search-panel {
  padding: 16px;

  margin-bottom: 20px;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  padding: 4px;
  position: relative;
}

.icon-user {
  position: absolute;
  left: 16px;
  color: var(--text-muted);
}

.input-wrapper input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  padding: 14px 16px 14px 48px;
  font-size: 1.1rem;
  outline: none;
}

.btn-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--accent-orange);
  color: #000;
  border: none;
  padding: 12px 24px;

  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}
.btn-search:hover { filter: brightness(1.15); }

.btn-stop {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(239, 68, 68, 0.2);
  color: var(--accent-red);
  border: 1px solid rgba(239, 68, 68, 0.4);
  padding: 12px 24px;

  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
}
.btn-stop:hover { background: rgba(239, 68, 68, 0.3); }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

/* ── Progress ─────────────────────────────────── */
.progress-area {
  margin-bottom: 24px;
  padding: 0 4px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.status-badge.scanning { color: var(--accent-orange); }
.status-badge.done { color: var(--accent-green); }
.status-badge.error { color: var(--accent-red); }

.pulse-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-orange);

  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(var(--accent-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0); }
}

.progress-track {
  height: 3px;
  background: var(--overlay-8);

  overflow: hidden;
}
.progress-fill.indeterminate {
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, var(--accent-orange), #ff3366);

  animation: indeterminate 1.4s ease-in-out infinite;

}
@keyframes indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

/* ── Profile Card ─────────────────────────────── */
.ghunt-results {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 32px;
}

.profile-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--accent-orange);

  padding: 24px;
  transition: all 0.25s ease;
}
.profile-card:hover {
  border-color: rgba(var(--accent-rgb), 0.3);

}

.profile-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar-container {
  position: relative;
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.avatar {
  width: 100%;
  height: 100%;

  object-fit: cover;
  border: 2px solid var(--border-color);
}

.avatar-placeholder {
  width: 100%;
  height: 100%;

  border: 2px solid var(--border-color);
  background: var(--bg-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.default-badge {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.8);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.6rem;
  padding: 1px 6px;

  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.profile-main-info h2 {
  margin: 0 0 8px 0;
  font-size: 1.4rem;
  color: var(--text-main);
  font-weight: 600;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 0.9rem;
}

.info-icon.accent { color: var(--accent-orange); }
.info-icon.muted { color: var(--text-muted); }

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
}

:deep(.inline-btn) {
  margin-left: 4px;
}

/* ── Details Grid ─────────────────────────────── */
.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.detail-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);

  padding: 20px;
  transition: all 0.25s ease;
}
.detail-card:hover {
  border-color: rgba(var(--accent-rgb), 0.25);

}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-orange);
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.detail-rows {
  display: flex;
  flex-direction: column;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 8px 0;
  gap: 12px;
}
.detail-row + .detail-row {
  border-top: 1px solid var(--border-color);
}

.dl {
  font-size: 0.82rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.dv {
  font-size: 0.88rem;
  color: var(--text-main);
  font-weight: 500;
  text-align: right;
}

.services-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.service-badge {
  background: rgba(var(--accent-rgb), 0.08);
  color: var(--accent-orange);
  border: 1px solid rgba(var(--accent-rgb), 0.2);
  padding: 5px 12px;

  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.2s;
}
.service-badge:hover {
  background: rgba(var(--accent-rgb), 0.15);
}

.empty-card-text {
  font-size: 0.85rem;
}

.text-green { color: var(--accent-green, #00ff88); }

/* ── Empty State ──────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 48px;
  text-align: center;
}

.empty-icon-wrapper {
  width: 96px;
  height: 96px;

  background: var(--overlay-8);
  border: 1px dashed var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.empty-state h3 {
  font-size: 1.5rem;
  color: var(--text-main);
  margin-bottom: 8px;
}

.empty-state p {
  color: var(--text-muted);
  max-width: 400px;
}

/* Auth Modal Styles */
.auth-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.auth-modal {
  padding: 32px;
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  text-align: center;
}

.auth-header h3 {
  font-size: 1.3rem;
  color: var(--accent-orange);
  margin-bottom: 8px;
}

.auth-desc {
  font-size: 0.95rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
:deep(.auth-desc a) {
  color: var(--accent-orange);
  text-decoration: underline;
}

.code-input {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  padding: 14px;
  color: var(--text-main);
  font-size: 1rem;
  width: 100%;
  text-align: center;
}

.code-input:focus {
  border-color: var(--accent-orange);
  outline: none;
}

.text-error { color: var(--accent-red); font-size: 0.85rem; margin-top: 4px; display: block; }

.auth-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-main);
  cursor: pointer;
  font-weight: 500;
}

.btn-primary {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--accent-orange);
  color: #000;
  border: none;
  font-weight: 600;
  cursor: pointer;
  padding: 12px;
}
.btn-primary:disabled, .btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
