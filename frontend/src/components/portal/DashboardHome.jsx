import { useState } from 'react'
import {
  formatDelta,
  anomalyFor,
  assessmentFor,
  buildInsights,
  buildNotifications,
  greetingFor,
  healthStatusFor,
  KEY_METRICS,
  latestValue,
  missionInfoFor,
} from '../../lib/portal'
import {
  formatMetric,
  formatRelativeTime,
  METRIC_META,
} from '../../lib/format'
import {
  Avatar,
  HistoryTable,
  InfoNote,
  InsightCard,
  MeasurementCard,
  NotificationItem,
  Panel,
  RangeTabs,
  SectionHeading,
  StatusPill,
  TrendGrid,
} from './shared'
import PortalIcon from './PortalIcon'

export default function DashboardHome({
  analysis,
  readings,
  profile,
  onNavigate,
}) {
  const [rangeDays, setRangeDays] = useState(14)
  const status = healthStatusFor(analysis)
  const insights = buildInsights(analysis)
  const notifications = buildNotifications(analysis)
  const mission = missionInfoFor(readings, profile)
  const firstName = profile.full_name.split(' ')[0]
  const latest = analysis.reading
  const messageNotifications = notifications.filter(
    (notification) => notification.category === 'Message',
  )

  return (
    <>
      <section className="portal-hero">
        <div className="hero-copy">
          <p className="portal-kicker">{greetingFor()}</p>
          <h1>
            {greetingFor()}, {firstName}
          </h1>
          <p className="hero-meta">
            {profile.astronaut_id} · {profile.mission_name}
          </p>

          <div className="hero-chips">
            <span className="mission-pill">
              <span className="mission-dot" />
              Mission active
            </span>
            <span className="hero-chip">
              {profile.mission_role}
            </span>
            <span className="hero-chip">
              Monitoring since {mission.startLabel}
            </span>
          </div>

          <div className="hero-status">
            <StatusPill
              severity={status.severity}
              label={status.label}
            />
            <p>{status.description}</p>
          </div>
        </div>

        <div className="hero-profile">
          <Avatar profile={profile} size="large" />
          <div className="hero-profile-copy">
            <strong>{profile.full_name}</strong>
            <span>{profile.astronaut_id}</span>
            <span className="hero-last-reading">
              Last reading {formatRelativeTime(latest.recorded_at)}
            </span>
          </div>
          <div className="hero-mission-day">
            <strong>{mission.days ?? '—'}</strong>
            <span>days monitored</span>
          </div>
        </div>
      </section>

      <Panel>
        <SectionHeading
          eyebrow="My health"
          title="Your health overview"
          description="Here is your latest recorded health information."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('health')}
            >
              View my health
            </button>
          }
        />

        <div className="measurement-grid">
          {KEY_METRICS.map((metric) => (
            <MeasurementCard
              key={metric}
              metric={metric}
              analysis={analysis}
            />
          ))}
        </div>

        <InfoNote>
          * Assessments are generated from your latest validated
          measurements and personal baselines. They are not a medical
          diagnosis.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Over time"
          title="My health trends"
          description="How your key measurements are changing, compared with your personal baseline."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('trends')}
            >
              View all trends
            </button>
          }
        />

        <div className="portal-toolbar">
          <RangeTabs value={rangeDays} onChange={setRangeDays} />
        </div>

        <TrendGrid
          analysis={analysis}
          readings={readings}
          metrics={KEY_METRICS}
          rangeDays={rangeDays}
        />
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Personal reference"
          title="My personal baselines"
          description="Your established range, with the latest measurement for comparison."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('baselines')}
            >
              View baselines
            </button>
          }
        />

        <div className="baseline-mini-grid">
          {KEY_METRICS.map((metric) => {
            const meta = METRIC_META[metric]
            const anomaly = anomalyFor(analysis, metric)
            const assessment = assessmentFor(analysis, metric)

            return (
              <article className="baseline-mini" key={metric}>
                <div className="baseline-mini-head">
                  <span>{meta.label}</span>
                  <StatusPill
                    severity={assessment.severity}
                    label={assessment.label}
                  />
                </div>
                <div className="baseline-mini-values">
                  <div>
                    <span>Baseline</span>
                    <strong>
                      {formatMetric(
                        anomaly?.baseline_value,
                        meta.unit,
                      )}
                    </strong>
                  </div>
                  <div>
                    <span>Current</span>
                    <strong>
                      {formatMetric(
                        latestValue(analysis, metric),
                        meta.unit,
                      )}
                    </strong>
                  </div>
                </div>
                <span className="baseline-delta">
                  {formatDelta(anomaly?.difference, meta.unit)}
                </span>
              </article>
            )
          })}
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Intelligence"
          title="My health insights"
          description="Plain-language explanations based on your latest assessment."
          action={
            <button
              className="link-button"
              type="button"
              onClick={() => onNavigate('insights')}
            >
              All insights
            </button>
          }
        />

        <div className="insight-list">
          {insights.slice(0, 2).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      </Panel>

      <div className="portal-split">
        <Panel>
          <SectionHeading
            eyebrow="Updates"
            title="My notifications"
            description="New assessments, alerts and monitoring updates."
            action={
              <button
                className="link-button"
                type="button"
                onClick={() => onNavigate('notifications')}
              >
                View all
              </button>
            }
          />

          {notifications.length > 0 ? (
            <ul className="notification-list">
              {notifications.slice(0, 3).map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                />
              ))}
            </ul>
          ) : (
            <InfoNote>No new notifications.</InfoNote>
          )}

          <div className="portal-message-note">
            <PortalIcon name="message" />
            <div>
              <strong>Mission medical messages</strong>
              <p>
                {messageNotifications.length > 0
                  ? messageNotifications[0].body
                  : 'No new messages from mission medical personnel.'}
              </p>
            </div>
          </div>
        </Panel>

        <Panel>
          <SectionHeading
            eyebrow="Recent measurements"
            title="My health history"
            description="Your latest recorded readings."
            action={
              <button
                className="link-button"
                type="button"
                onClick={() => onNavigate('history')}
              >
                Full history
              </button>
            }
          />

          <HistoryTable readings={readings} limit={5} />
        </Panel>
      </div>

      <p className="portal-disclaimer">
        Health assessments support mission monitoring and do not
        replace evaluation by mission medical personnel. Values shown
        are based on the latest stored reading.
      </p>
    </>
  )
}
