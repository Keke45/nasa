import { useState } from 'react'
import {
  InfoNote,
  Panel,
  SectionHeading,
} from './shared'

const STORAGE_KEY = 'nasa.portal.preferences'

const PREFERENCE_OPTIONS = [
  {
    key: 'health_alerts',
    title: 'Health alerts',
    description:
      'Show alerts when a measurement falls outside your personal baseline.',
  },
  {
    key: 'sleep_reminders',
    title: 'Sleep reminders',
    description:
      'Show recovery guidance when your sleep duration is below baseline.',
  },
  {
    key: 'weekly_summary',
    title: 'Weekly summary',
    description:
      'Show a weekly summary of trends and monitoring activity.',
  },
  {
    key: 'medical_messages',
    title: 'Mission medical messages',
    description:
      'Show messages from authorised mission medical personnel.',
  },
]

const DEFAULT_PREFERENCES = {
  health_alerts: true,
  sleep_reminders: true,
  weekly_summary: true,
  medical_messages: true,
}

function loadPreferences() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      return DEFAULT_PREFERENCES
    }
    return {
      ...DEFAULT_PREFERENCES,
      ...JSON.parse(stored),
    }
  } catch {
    return DEFAULT_PREFERENCES
  }
}

function Toggle({ checked, onChange, label }) {
  return (
    <button
      className={`portal-toggle ${checked ? 'is-on' : ''}`}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  )
}

export default function SettingsView({ profile, analysis, readings }) {
  const [preferences, setPreferences] = useState(loadPreferences)
  const [saved, setSaved] = useState(true)

  function updatePreference(key, value) {
    const next = { ...preferences, [key]: value }
    setPreferences(next)
    setSaved(false)

    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(next),
      )
      setSaved(true)
    } catch {
      setSaved(false)
    }
  }

  function downloadData() {
    const payload = {
      exported_at: new Date().toISOString(),
      profile,
      latest_analysis: analysis,
      readings,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${profile.astronaut_id}-health-data.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="Account settings"
          title="Your account"
          description="Account details are managed by mission operations."
        />

        <div className="settings-account">
          <div>
            <span>Name</span>
            <strong>{profile.full_name}</strong>
          </div>
          <div>
            <span>Astronaut ID</span>
            <strong>{profile.astronaut_id}</strong>
          </div>
          <div>
            <span>Mission</span>
            <strong>{profile.mission_name}</strong>
          </div>
          <div>
            <span>Role</span>
            <strong>{profile.mission_role}</strong>
          </div>
        </div>

        <InfoNote>
          To update your name, mission assignment or account access,
          contact mission operations.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Preferences"
          title="Notification preferences"
          description="Choose which monitoring updates appear in your portal."
          action={
            <span
              className={`save-indicator ${
                saved ? 'is-saved' : ''
              }`}
            >
              {saved ? 'Saved on this device' : 'Not saved'}
            </span>
          }
        />

        <div className="preference-list">
          {PREFERENCE_OPTIONS.map((option) => (
            <div className="preference-item" key={option.key}>
              <div>
                <strong>{option.title}</strong>
                <p>{option.description}</p>
              </div>
              <Toggle
                checked={preferences[option.key]}
                onChange={(value) =>
                  updatePreference(option.key, value)
                }
                label={option.title}
              />
            </div>
          ))}
        </div>

        <InfoNote>
          These preferences are stored on this device for the portal
          display. Mission medical notifications are delivered
          according to mission operations procedures.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Data"
          title="My health data"
          description="Download a copy of the health data shown in this portal."
          action={
            <button
              className="primary-button"
              type="button"
              onClick={downloadData}
            >
              Download my data
            </button>
          }
        />

        <div className="settings-account">
          <div>
            <span>Stored readings</span>
            <strong>{readings.length}</strong>
          </div>
          <div>
            <span>Latest reading</span>
            <strong>{analysis.reading.recorded_at.slice(0, 10)}</strong>
          </div>
          <div>
            <span>Baseline version</span>
            <strong>{analysis.baseline.version ?? '—'}</strong>
          </div>
          <div>
            <span>Assessment status</span>
            <strong>
              {analysis.summary.anomaly.highest_severity}
            </strong>
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Privacy"
          title="Who can access my data"
          description="Your health information is handled under mission medical protocols."
        />

        <div className="profile-access-list">
          <div>
            <strong>You</strong>
            <p>
              You can view and download your own health data from this
              portal.
            </p>
          </div>
          <div>
            <strong>Authorised mission medical personnel</strong>
            <p>
              Medical personnel can review your records and manage
              alerts when authorised.
            </p>
          </div>
          <div>
            <strong>Other astronauts</strong>
            <p>
              Other crew members cannot view your personal health
              information from this portal.
            </p>
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionHeading title="Need help?" />
        <div className="settings-help">
          <p>
            For clinical questions or symptoms, contact mission
            medical personnel directly.
          </p>
          <p>
            For account access, mission assignment or portal issues,
            contact mission operations.
          </p>
        </div>
      </Panel>
    </>
  )
}
