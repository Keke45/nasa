import {
  formatDate,
  formatRelativeTime,
} from '../../lib/format'
import {
  healthStatusFor,
  missionInfoFor,
} from '../../lib/portal'
import {
  Avatar,
  InfoNote,
  Panel,
  SectionHeading,
  StatusPill,
} from './shared'

function Fact({ label, value }) {
  return (
    <div className="profile-fact">
      <span>{label}</span>
      <strong>{value || '—'}</strong>
    </div>
  )
}

export default function ProfileView({
  profile,
  analysis,
  readings,
}) {
  const mission = missionInfoFor(readings, profile)
  const status = healthStatusFor(analysis)
  const latest = analysis.reading
  const baseline = analysis.baseline

  return (
    <>
      <Panel className="profile-hero-panel">
        <div className="profile-hero">
          <Avatar profile={profile} size="large" />
          <div className="profile-identity">
            <p className="portal-kicker">Astronaut profile</p>
            <h1>{profile.full_name}</h1>
            <p className="profile-subtitle">
              {profile.astronaut_id} · {profile.mission_name}
            </p>
            <div className="profile-badges">
              <StatusPill
                severity={status.severity}
                label={status.label}
              />
              <span className="mission-pill">
                <span className="mission-dot" />
                Mission active
              </span>
            </div>
          </div>

          <div className="profile-mission-day">
            <strong>{mission.days ?? '—'}</strong>
            <span>days monitored</span>
            <small>{mission.status}</small>
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Mission"
          title="Mission information"
          description="Your current mission assignment and monitoring window."
        />

        <div className="profile-facts">
          <Fact label="Astronaut ID" value={profile.astronaut_id} />
          <Fact label="Mission" value={profile.mission_name} />
          <Fact label="Mission role" value={profile.mission_role} />
          <Fact label="Nationality" value={profile.nationality} />
          <Fact
            label="Date of birth"
            value={
              profile.date_of_birth
                ? formatDate(profile.date_of_birth)
                : ''
            }
          />
          <Fact label="Monitoring start" value={mission.startLabel} />
          <Fact
            label="Expected return"
            value={
              profile.expected_return_date
                ? formatDate(profile.expected_return_date)
                : ''
            }
          />
          <Fact
            label="Latest reading"
            value={formatDate(latest.recorded_at)}
          />
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Monitoring"
          title="My health monitoring profile"
          description="The baseline and assessment setup behind your dashboard."
        />

        <div className="profile-facts">
          <Fact
            label="Health status"
            value={`${status.label} · ${status.description}`}
          />
          <Fact
            label="Baseline version"
            value={
              baseline.version
                ? `Version ${baseline.version}`
                : 'Not established'
            }
          />
          <Fact
            label="Baseline window"
            value={
              baseline.window_days
                ? `${baseline.window_days} days`
                : '—'
            }
          />
          <Fact
            label="Evaluated metrics"
            value={`${baseline.usable_count}/${baseline.metric_count}`}
          />
          <Fact
            label="Stored readings"
            value={`${readings.length}`}
          />
          <Fact
            label="Data freshness"
            value={formatRelativeTime(latest.recorded_at)}
          />
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          title="Profile and privacy"
          description="Who can see this information."
        />
        <div className="profile-access-list">
          <div>
            <strong>You</strong>
            <p>
              You can view your personal health measurements,
              baselines, insights and history.
            </p>
          </div>
          <div>
            <strong>Authorised mission medical personnel</strong>
            <p>
              Medical personnel can review your health records and
              manage alerts when authorised.
            </p>
          </div>
          <div>
            <strong>Other astronauts</strong>
            <p>
              Other crew members cannot view your personal health
              data from this portal.
            </p>
          </div>
        </div>
        <InfoNote>
          Profile details are shown from astronaut registration when
          available. Monitoring data is always linked to your
          astronaut ID.
        </InfoNote>
      </Panel>
    </>
  )
}
