import type { Topic, TopicItem } from '../app/types';

type ItemTTSState = {
  jobId: string;
  status: string;
  progress: number;
  message?: string | null;
  outputRef?: string | null;
};

type Props = {
  topics: Topic[];
  selectedTopicId: string;
  selectedTopicName: string;
  items: TopicItem[];
  isLoadingItems: boolean;
  ttsByItem: Record<string, ItemTTSState>;
  ttsModeByItem: Record<string, 'tts_full_page' | 'tts_summary'>;
  playingItemId: string | null;
  onSelectTopic: (topicId: string) => void;
  onSetMode: (itemId: string, mode: 'tts_full_page' | 'tts_summary') => void;
  onQueueTTS: (itemId: string, mode: 'tts_full_page' | 'tts_summary') => void;
  onPlayPause: (item: TopicItem, state: ItemTTSState) => void;
};

export function AudioPane({
  topics,
  selectedTopicId,
  selectedTopicName,
  items,
  isLoadingItems,
  ttsByItem,
  ttsModeByItem,
  playingItemId,
  onSelectTopic,
  onSetMode,
  onQueueTTS,
  onPlayPause,
}: Props) {
  return (
    <div className="audio-pane">
      <div className="audio-pane-sticky">
        <section className="topic-strip">
          {topics.map((topic) => (
            <button
              className={`topic-chip ${selectedTopicId === topic.topic_id ? 'active' : ''}`}
              key={topic.topic_id}
              onClick={() => onSelectTopic(topic.topic_id)}
            >
              <span className="topic-icon">{topic.icon || '•'}</span>
              <span>{topic.name}</span>
            </button>
          ))}
        </section>
      </div>

      {isLoadingItems ? (
        <section className="items-grid">
          {Array.from({ length: 6 }).map((_, idx) => (
            <article key={idx} className="item-card skeleton-card">
              <div className="skeleton-line w-70" />
              <div className="skeleton-line w-45" />
              <div className="skeleton-block" />
              <div className="skeleton-line w-80" />
              <div className="skeleton-line w-55" />
            </article>
          ))}
        </section>
      ) : (
        <section className="items-grid">
          {items.map((item) => {
            const row = ttsByItem[item.item_id];
            const isActive = row && (row.status === 'queued' || row.status === 'processing');
            const isReady = row?.status === 'ready';
            const isPlaying = playingItemId === item.item_id;
            const mode = ttsModeByItem[item.item_id] || 'tts_summary';
            return (
              <article key={item.item_id} className="item-card">
                <div className="card-head">
                  <h3>{item.title}</h3>
                  <span className="source-badge">{item.source_name || 'Source'}</span>
                </div>

                <div className="meta-row">
                  <span>{formatRelativeTime(item.published_at)}</span>
                  <span>•</span>
                  <span>{selectedTopicName || selectedTopicId}</span>
                </div>

                {item.summary ? <p className="snippet">{item.summary}</p> : null}
                {item.image_url ? <img className="item-image" src={item.image_url} alt="" /> : null}

                <div className="action-row">
                  <a className="source-link" href={item.url} target="_blank" rel="noreferrer">
                    Open Source ↗
                  </a>
                  <div className="mode-toggle">
                    <button className={mode === 'tts_summary' ? 'active' : ''} onClick={() => onSetMode(item.item_id, 'tts_summary')}>
                      Summary
                    </button>
                    <button className={mode === 'tts_full_page' ? 'active' : ''} onClick={() => onSetMode(item.item_id, 'tts_full_page')}>
                      Full
                    </button>
                  </div>
                </div>

                <div className="item-actions">
                  {isActive ? (
                    <div className="inline-progress">
                      <div className="inline-progress-track">
                        <div className="inline-progress-fill" style={{ width: `${row.progress}%` }} />
                      </div>
                      <span>
                        {row.status} {row.progress}%
                      </span>
                    </div>
                  ) : isReady && row ? (
                    <button className="primary-btn" onClick={() => onPlayPause(item, row)}>
                      {isPlaying ? 'Pause' : 'Play'}
                    </button>
                  ) : (
                    <button className="primary-btn" onClick={() => onQueueTTS(item.item_id, mode)}>
                      Queue TTS
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}

function formatRelativeTime(value?: string | null): string {
  if (!value) {
    return 'Unknown time';
  }
  const now = Date.now();
  const target = new Date(value).getTime();
  if (Number.isNaN(target)) {
    return 'Unknown time';
  }
  const diffMins = Math.max(0, Math.floor((now - target) / 60000));
  if (diffMins < 1) {
    return 'Just now';
  }
  if (diffMins < 60) {
    return `${diffMins}m ago`;
  }
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
