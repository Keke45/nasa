import { useState } from 'react'
import { formatDate } from '../../lib/format'
import {
  buildInsights,
  healthStatusFor,
} from '../../lib/portal'
import { getAnalysis } from '../../services/api'
import {
  EmptyState,
  HistoryTable,
  InfoNote,
  Panel,
  SectionHeading,
  StatusPill,
} from './shared'

const DAY_MS = 24 * 60 * 60 * 1000

const RANGES = [
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 'all', label: 'All readings' },
]

function filterReadings(readings, range) {
  if (range === 'all' || readings.length === 0) {
    return readings
  }

  const latest = new Date(
    readings[readings.length - 1].recorded_at,
  ).getTime()

  return readings.filter(
    (reading) =>
      latest - new Date(reading.recorded_at).getTime() <=
      range * DAY_MS,
  )
}

export default function HistoryView({
  analysis,
  readings,
  profile,
}) {
  const [range, setRange] = useState(30)
  const [visibleCount, setVisibleCount] = useState(20)
  const [previous, setPrevious] = useState([])
  const [loadingPrevious, setLoadingPrevious] = useState(false)
  const [previousError, setPreviousError] = useState('')

  const filtered = filterReadings(readings, range)
  const latestStatus = healthStatusFor(analysis)
  const latestInsights = buildInsights(analysis)

  async function loadPrevious() {
    const candidates = [...readings]
      .reverse()
      .filter((reading) => reading.id !== analysis.reading.id)
      .slice(0, 3)

    if (candidates.length === 0) {
      setPreviousError(
        'There are no earlier readings available for assessment.',
      )
      return
    }

    setLoadingPrevious(true)
    setPreviousError('')

    const results = await Promise.allSettled(
      candidates.map((reading) =>
        getAnalysis(profile.astronaut_id, {
          readingId: reading.id,
        }),
      ),
    )

    const loaded = results
      .map((result, index) => {
        if (result.status !== 'fulfilled') {
          return null
        }

        return {
          reading: candidates[index],
          analysis: result.value,
          status: healthStatusFor(result.value),
          insights: buildInsights(result.value),
        }
      })
      .filter(Boolean)

    setPrevious(loaded)
    setLoadingPrevious(false)

    if (loaded.length === 0) {
      setPreviousError(
        'Previous assessments could not be calculated right now.',
      )
    }
  }

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="Health history"
          title="Your measurement record"
          description={`${readings.length} readings stored · latest on ${formatDate(
            analysis.reading.recorded_at,
          )}`}
        />

        <div className="portal-toolbar">
          <div className="filter-tabs" role="tablist">
            {RANGES.map((option) => (
              <button
                key={option.value}
                className={`filter-tab ${
                  range === option.value ? 'is-active' : ''
                }`}
                type="button"
                role="tab"
                aria-selected={range === option.value}
                onClick={() => {
                  setRange(option.value)
                  setVisibleCount(20)
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
          <span className="section-note">
            {filtered.length} readings in this range
          </span>
        </div>

        <HistoryTable
          readings={filtered}
          limit={visibleCount}
        />

        {filtered.length > visibleCount && (
          <div className="history-more">
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                setVisibleCount((count) => count + 20)
              }
            >
              Show more readings
            </button>
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Latest assessment"
          title="Your most recent result"
          description="The assessment currently shown across your dashboard."
          action={
            <StatusPill
              severity={latestStatus.severity}
              label={latestStatus.label}
            />
          }
        />

        <div className="assessment-summary">
          <div>
            <span>Reading date</span>
            <strong>{formatDate(analysis.reading.recorded_at)}</strong>
          </div>
          <div>
            <span>Top finding</span>
            <strong>{latestInsights[0]?.title}</strong>
            <p>{latestInsights[0]?.observation}</p>
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Previous assessments"
          title="Earlier health assessments"
          description="Recalculate the assessment for your three most recent earlier readings."
          action={
            <button
              className="secondary-button"
              type="button"
              onClick={loadPrevious}
              disabled={loadingPrevious}
            >
              {loadingPrevious
                ? 'Calculating…'
                : 'Load previous assessments'}
            </button>
          }
        />

        {previousError && <InfoNote>{previousError}</InfoNote>}

        {previous.length > 0 ? (
          <div className="previous-assessment-list">
            {previous.map((item) => (
              <article
                className="previous-assessment"
                key={item.reading.id}
              >
                <div className="previous-assessment-head">
                  <div>
                    <span>
                      {formatDate(item.reading.recorded_at)}
                    </span>
                    <strong>
                      {item.insights[0]?.title ??
                        'Assessment complete'}
                    </strong>
                  </div>
                  <StatusPill
                    severity={item.status.severity}
                    label={item.status.label}
                  />
                </div>
                <p>
                  {item.insights[0]?.observation ??
                    item.status.description}
                </p>
              </article>
            ))}
          </div>
        ) : (
          !loadingPrevious &&
          !previousError && (
            <EmptyState
              icon="history"
              title="No previous assessments loaded"
              description="Choose “Load previous assessments” to calculate results for earlier readings."
            />
          )
        )}

        <InfoNote>
          Previous assessments are calculated on demand with the
          currently stored personal baseline. They are not saved
          reports or historical clinical records.
        </InfoNote>
      </Panel>
    </>
  )
}
