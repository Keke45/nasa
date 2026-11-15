import { useState } from 'react'
import { buildNotifications } from '../../lib/portal'
import PortalIcon from './PortalIcon'
import {
  EmptyState,
  InfoNote,
  NotificationItem,
  Panel,
  SectionHeading,
} from './shared'

const FILTERS = [
  'All',
  'Health alert',
  'Sleep',
  'Assessment',
  'Monitoring',
]

export default function NotificationsView({ analysis }) {
  const [filter, setFilter] = useState('All')
  const notifications = buildNotifications(analysis)
  const unread = notifications.filter(
    (notification) => notification.unread,
  ).length
  const visible =
    filter === 'All'
      ? notifications
      : notifications.filter(
          (notification) => notification.category === filter,
        )

  return (
    <>
      <Panel>
        <SectionHeading
          eyebrow="Notifications"
          title="Your monitoring updates"
          description={
            unread > 0
              ? `${unread} unread update${
                  unread === 1 ? '' : 's'
                } from your latest assessment.`
              : 'No unread updates from your latest assessment.'
          }
        />

        <div className="portal-toolbar notification-toolbar">
          <div className="filter-tabs" role="tablist">
            {FILTERS.map((option) => {
              const count =
                option === 'All'
                  ? notifications.length
                  : notifications.filter(
                      (notification) =>
                        notification.category === option,
                    ).length

              return (
                <button
                  key={option}
                  className={`filter-tab ${
                    filter === option ? 'is-active' : ''
                  }`}
                  type="button"
                  role="tab"
                  aria-selected={filter === option}
                  onClick={() => setFilter(option)}
                >
                  {option}
                  <span>{count}</span>
                </button>
              )
            })}
          </div>
        </div>

        {visible.length > 0 ? (
          <ul className="notification-list">
            {visible.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
              />
            ))}
          </ul>
        ) : (
          <EmptyState
            icon="notifications"
            title="Nothing in this category"
            message="There are no notifications matching this filter."
          />
        )}
      </Panel>

      <Panel>
        <SectionHeading
          eyebrow="Messages"
          title="Mission medical messages"
          description="Direct messages from authorised mission medical personnel appear here."
        />

        <div className="message-center">
          <span className="message-center-icon">
            <PortalIcon name="message" />
          </span>
          <div>
            <strong>No new messages</strong>
            <p>
              There are no messages from mission medical personnel at
              this time. If you need to discuss a health concern,
              contact the medical team directly.
            </p>
          </div>
        </div>

        <InfoNote>
          Notifications are generated from your latest assessment and
          monitoring activity. They are not a diagnosis.
        </InfoNote>
      </Panel>
    </>
  )
}
