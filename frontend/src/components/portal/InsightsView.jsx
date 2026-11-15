import {
  formatMetric,
  formatNumber,
  METRIC_META,
} from '../../lib/format'
import { buildInsights } from '../../lib/portal'
import {
  InfoNote,
  InsightCard,
  Panel,
  SectionHeading,
  StatusPill,
} from './shared'

function mlSeverity(status) {
  if (status === 'ANOMALY') {
    return 'WATCH'
  }
  if (status === 'NORMAL') {
    return 'NORMAL'
  }
  return 'NOT_EVALUATED'
}

export default function InsightsView({ analysis }) {
  const insights = buildInsights(analysis)
  const ml = analysis.ml_anomaly
  const deviations = (ml.top_deviating_metrics || []).slice(0, 3)
  const score =
    typeof ml.anomaly_score === 'number'
      ? Math.round(ml.anomaly_score * 100)
      : null

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="AI health insights"
          title="What your health data is telling you"
          description="Plain-language observations based on your latest reading, personal baseline and alert rules."
        />

        <div className="insight-list">
          {insights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>

        <InfoNote>
          These insights explain monitoring results. They are not a
          diagnosis and do not replace evaluation by mission medical
          personnel.
        </InfoNote>
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Pattern check"
          title="Personal anomaly model"
          description="A model trained on your previous measurements looks for unusual combinations of values."
          action={
            <StatusPill
              severity={mlSeverity(ml.status)}
              label={ml.status || 'Unavailable'}
            />
          }
        />

        <div className="ml-panel">
          <div className="ml-score">
            <span>Unusualness score</span>
            <strong>{score === null ? '—' : `${score}%`}</strong>
            <p>
              A higher score means the reading is more unusual for
              your personal history.
            </p>
          </div>
          <div className="ml-reason">
            <strong>What the model found</strong>
            <p>
              {ml.reason ||
                'No personal anomaly result is available for this reading.'}
            </p>
            {ml.in_sample && (
              <span className="ml-warning">
                This reading was part of the model's training data, so
                the result may be optimistic.
              </span>
            )}
          </div>
        </div>

        {deviations.length > 0 && (
          <div className="ml-deviation-grid">
            {deviations.map((item) => (
              <article key={item.metric}>
                <span>
                  {item.metric_label ||
                    METRIC_META[item.metric]?.label ||
                    item.metric}
                </span>
                <strong>
                  {formatMetric(item.value, item.unit || '')}
                </strong>
                <p>
                  {Math.abs(item.z_score) >= 1 ? '+' : ''}
                  {formatNumber(item.z_score, 1)} standard deviations
                  from your model average
                </p>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Guidance"
          title="How to use these insights"
          description="Suggested next steps are general wellbeing guidance."
        />
        <div className="baseline-guide">
          <article>
            <strong>Use them as prompts</strong>
            <p>
              Insights highlight measurements worth paying attention
              to. They are not instructions to change medication or
              treatment.
            </p>
          </article>
          <article>
            <strong>Watch the pattern</strong>
            <p>
              A single unusual reading matters less than a sustained
              change. Use health trends to see whether a pattern is
              developing.
            </p>
          </article>
          <article>
            <strong>Contact mission medical</strong>
            <p>
              If a symptom worries you, or an alert persists, contact
              authorised mission medical personnel directly.
            </p>
          </article>
        </div>
      </Panel>
    </>
  )
}
