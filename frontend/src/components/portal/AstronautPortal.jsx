import { useCallback, useEffect, useState } from 'react'
import {
  buildNotifications,
  missionInfoFor,
  PORTAL_ASTRONAUT_ID,
  profileFor,
} from '../../lib/portal'
import { formatRelativeTime } from '../../lib/format'
import {
  getAnalysis,
  getAstronautDirectory,
  getReadings,
} from '../../services/api'
import { Avatar } from './shared'
import PortalIcon from './PortalIcon'
import DashboardHome from './DashboardHome'
import ProfileView from './ProfileView'
import HealthView from './HealthView'
import MetricFocusView from './MetricFocusView'
import TrendsView from './TrendsView'
import BaselinesView from './BaselinesView'
import InsightsView from './InsightsView'
import NotificationsView from './NotificationsView'
import HistoryView from './HistoryView'
import SettingsView from './SettingsView'

const ALL_VIEWS = [
  {
    id: 'dashboard',
    label: 'My Dashboard',
    icon: 'dashboard',
    title: 'My dashboard',
    subtitle: 'Your health at a glance.',
  },
  {
    id: 'profile',
    label: 'My Profile',
    icon: 'profile',
    title: 'My profile',
    subtitle: 'Your mission assignment and monitoring setup.',
  },
  {
    id: 'health',
    label: 'My Health',
    icon: 'health',
    title: 'My health',
    subtitle: 'Your latest measurements and assessment.',
  },
  {
    id: 'sleep',
    label: 'Sleep Monitoring',
    icon: 'sleep',
    title: 'Sleep monitoring',
    subtitle: 'Your sleep duration and recovery pattern.',
  },
  {
    id: 'activity',
    label: 'Physical Activity',
    icon: 'activity',
    title: 'Physical activity',
    subtitle: 'Your movement and recovery balance.',
  },
  {
    id: 'trends',
    label: 'Health Trends',
    icon: 'trends',
    title: 'Health trends',
    subtitle: 'How your measurements are changing over time.',
  },
  {
    id: 'baselines',
    label: 'My Baselines',
    icon: 'baseline',
    title: 'My baselines',
    subtitle: 'Your personal reference range.',
  },
  {
    id: 'insights',
    label: 'Health Insights',
    icon: 'insights',
    title: 'Health insights',
    subtitle: 'What your health data is telling you.',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    icon: 'notifications',
    title: 'Notifications',
    subtitle: 'Monitoring updates and medical messages.',
  },
  {
    id: 'history',
    label: 'Health History',
    icon: 'history',
    title: 'Health history',
    subtitle: 'Your stored measurements and earlier assessments.',
  },
  {
    id: 'settings',
    label: 'Account Settings',
    icon: 'settings',
    title: 'Account settings',
    subtitle: 'Preferences, data and privacy.',
  },
]

const ACCOUNT_VIEW_IDS = ['profile', 'settings']
const SIDEBAR_HIDDEN_IDS = [
  ...ACCOUNT_VIEW_IDS,
  'sleep',
  'activity',
  'baselines',
  'history',
  'notifications',
]
const NAV_ITEMS = ALL_VIEWS.filter(
  (item) => !SIDEBAR_HIDDEN_IDS.includes(item.id),
)
const ACCOUNT_ITEMS = ALL_VIEWS.filter((item) =>
  ACCOUNT_VIEW_IDS.includes(item.id),
)

function RefreshIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-2.6-6.4L21 8" />
      <path d="M21 3v5h-5" />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function loadTheme() {
  try {
    const stored = window.localStorage.getItem('nasa.portal.theme')
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {}

  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export default function AstronautPortal() {
  const [view, setView] = useState('dashboard')
  const [theme, setTheme] = useState(loadTheme)
  const [analysis, setAnalysis] = useState(null)
  const [readings, setReadings] = useState([])
  const [directoryEntry, setDirectoryEntry] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [lastSynced, setLastSynced] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError('')
    setNotice('')

    const [analysisResult, readingsResult, directoryResult] =
      await Promise.allSettled([
        getAnalysis(PORTAL_ASTRONAUT_ID),
        getReadings(PORTAL_ASTRONAUT_ID),
        getAstronautDirectory(),
      ])

    if (analysisResult.status === 'fulfilled') {
      setAnalysis(analysisResult.value)
    } else {
      setError(
        analysisResult.reason?.message ||
          'Unable to load your health assessment.',
      )
    }

    if (readingsResult.status === 'fulfilled') {
      setReadings(readingsResult.value.readings ?? [])
    } else {
      setReadings([])
      setNotice(
        'Measurement history could not be loaded right now. Your latest assessment is still available.',
      )
    }

    if (directoryResult.status === 'fulfilled') {
      const match = directoryResult.value.find(
        (entry) =>
          (entry.astronaut_id ?? entry.id) === PORTAL_ASTRONAUT_ID,
      )
      setDirectoryEntry(match ?? null)
    } else {
      setDirectoryEntry(null)
    }

    setLastSynced(new Date().toISOString())
    setLoading(false)
    setRefreshing(false)
  }, [])

  useEffect(() => {
    let active = true

    Promise.resolve().then(() => {
      if (active) {
        loadData()
      }
    })

    return () => {
      active = false
    }
  }, [loadData])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme

    try {
      window.localStorage.setItem('nasa.portal.theme', theme)
    } catch {}
  }, [theme])

  useEffect(() => {
    if (!accountMenuOpen) {
      return undefined
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setAccountMenuOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [accountMenuOpen])

  const profile = profileFor(PORTAL_ASTRONAUT_ID, directoryEntry)
  const activeItem =
    ALL_VIEWS.find((item) => item.id === view) ?? ALL_VIEWS[0]
  const unreadCount = analysis
    ? buildNotifications(analysis).filter(
        (notification) => notification.unread,
      ).length
    : 0

  function showView(nextView) {
    setView(nextView)
    setSidebarOpen(false)
    setAccountMenuOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function renderView() {
    if (!analysis) {
      return null
    }

    switch (view) {
      case 'profile':
        return (
          <ProfileView
            profile={profile}
            analysis={analysis}
            readings={readings}
          />
        )
      case 'health':
        return (
          <HealthView
            analysis={analysis}
            readings={readings}
            onNavigate={showView}
          />
        )
      case 'sleep':
        return (
          <MetricFocusView
            metric="sleep_duration"
            analysis={analysis}
            readings={readings}
            onNavigate={showView}
          />
        )
      case 'activity':
        return (
          <MetricFocusView
            metric="physical_activity"
            analysis={analysis}
            readings={readings}
            onNavigate={showView}
          />
        )
      case 'trends':
        return (
          <TrendsView analysis={analysis} readings={readings} />
        )
      case 'baselines':
        return <BaselinesView analysis={analysis} />
      case 'insights':
        return <InsightsView analysis={analysis} />
      case 'notifications':
        return <NotificationsView analysis={analysis} />
      case 'history':
        return (
          <HistoryView
            analysis={analysis}
            readings={readings}
            profile={profile}
          />
        )
      case 'settings':
        return (
          <SettingsView
            profile={profile}
            analysis={analysis}
            readings={readings}
          />
        )
      default:
        return (
          <DashboardHome
            analysis={analysis}
            readings={readings}
            profile={profile}
            onNavigate={showView}
          />
        )
    }
  }

  if (loading) {
    return (
      <div className="portal-loading">
        <span className="portal-spinner" />
        <strong>Loading your health portal</strong>
        <p>Retrieving your latest assessment and measurements.</p>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="portal-error-screen">
        <span className="portal-error-icon">
          <PortalIcon name="alert" />
        </span>
        <h1>Unable to load your health portal</h1>
        <p>{error || 'The health service is unavailable.'}</p>
        <button
          className="primary-button"
          type="button"
          onClick={() => loadData()}
        >
          Try again
        </button>
      </div>
    )
  }

  const mission = missionInfoFor(readings, profile)

  return (
    <div className="portal-shell">
      <aside
        className={`portal-sidebar ${
          sidebarOpen ? 'is-open' : ''
        }`}
      >
        <div className="portal-brand">
          <span className="portal-brand-mark">
            <PortalIcon name="mission" />
          </span>
          <span className="portal-brand-copy">
            <strong>NASA Health</strong>
            <span>Astronaut Portal</span>
          </span>
        </div>

        <div className="sidebar-mission">
          <span className="mission-pill">
            <span className="mission-dot" />
            Mission active
          </span>
          <p>{profile.mission_name}</p>
          <span>
            {mission.days === null
              ? 'Monitoring in progress'
              : `Day ${mission.days} of monitoring`}
          </span>
        </div>

        <nav className="portal-nav" aria-label="Personal health">
          <p className="portal-nav-label">My health</p>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`portal-nav-item ${
                view === item.id ? 'is-active' : ''
              }`}
              type="button"
              aria-current={view === item.id ? 'page' : undefined}
              onClick={() => showView(item.id)}
            >
              <PortalIcon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-account">
          {accountMenuOpen && (
            <div
              className="sidebar-account-menu"
              role="menu"
              aria-label="Profile and account"
            >
              {ACCOUNT_ITEMS.map((item) => (
                <button
                  key={item.id}
                  className={
                    view === item.id ? 'is-active' : undefined
                  }
                  type="button"
                  role="menuitem"
                  onClick={() => showView(item.id)}
                >
                  <PortalIcon name={item.icon} />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          )}

          <button
            className={`sidebar-profile ${
              accountMenuOpen ? 'is-open' : ''
            } ${
              ACCOUNT_VIEW_IDS.includes(view) ? 'is-active' : ''
            }`}
            type="button"
            aria-haspopup="menu"
            aria-expanded={accountMenuOpen}
            onClick={() =>
              setAccountMenuOpen((open) => !open)
            }
          >
            <Avatar profile={profile} size="small" />
            <span>
              <strong>{profile.full_name}</strong>
              <span>{profile.astronaut_id}</span>
            </span>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m9 18 6-6-6-6" />
            </svg>
          </button>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Close navigation"
          onClick={() => {
            setSidebarOpen(false)
            setAccountMenuOpen(false)
          }}
        />
      )}

      <div className="portal-main">
        <header className="portal-topbar">
          <button
            className="portal-menu-button"
            type="button"
            aria-label="Open navigation"
            onClick={() => setSidebarOpen(true)}
          >
            <MenuIcon />
          </button>

          <div className="portal-topbar-copy">
            <h2>{activeItem.title}</h2>
            <p>{activeItem.subtitle}</p>
          </div>

          <div className="portal-topbar-actions">
            <span className="sync-note">
              {lastSynced
                ? `Updated ${formatRelativeTime(lastSynced)}`
                : 'Not synced'}
            </span>
            <button
              className={`icon-button ${
                refreshing ? 'is-spinning' : ''
              }`}
              type="button"
              aria-label="Refresh health data"
              title="Refresh health data"
              onClick={() => loadData(true)}
              disabled={refreshing}
            >
              <RefreshIcon />
            </button>
            <button
              className="icon-button theme-toggle"
              type="button"
              aria-label={
                theme === 'dark'
                  ? 'Switch to light mode'
                  : 'Switch to dark mode'
              }
              title={
                theme === 'dark'
                  ? 'Switch to light mode'
                  : 'Switch to dark mode'
              }
              onClick={() =>
                setTheme((current) =>
                  current === 'dark' ? 'light' : 'dark',
                )
              }
            >
              <PortalIcon
                name={theme === 'dark' ? 'sun' : 'moon'}
              />
            </button>
            <button
              className={`icon-button notification-button ${
                view === 'notifications' ? 'is-active' : ''
              }`}
              type="button"
              aria-label={`Notifications${
                unreadCount > 0 ? `, ${unreadCount} unread` : ''
              }`}
              title="Notifications"
              onClick={() => showView('notifications')}
            >
              <PortalIcon name="notifications" />
              {unreadCount > 0 && (
                <span className="topbar-badge">{unreadCount}</span>
              )}
            </button>
            <Avatar profile={profile} size="small" />
          </div>
        </header>

        {error && (
          <div className="portal-banner">
            <span>{error}</span>
            <button
              className="link-button"
              type="button"
              onClick={() => loadData(true)}
            >
              Retry
            </button>
          </div>
        )}

        {notice && (
          <div className="portal-banner is-notice">
            <span>{notice}</span>
          </div>
        )}

        <main className="portal-content">{renderView()}</main>

        <footer className="portal-footer">
          <span>NASA Health Intelligence · Astronaut Portal</span>
          <span>
            Health data is visible to you and authorised mission
            medical personnel.
          </span>
        </footer>
      </div>
    </div>
  )
}
