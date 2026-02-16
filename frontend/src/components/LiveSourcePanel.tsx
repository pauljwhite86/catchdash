import type { LiveItem, LiveSourcePayload } from '../app/types';
import { LiveItemRow } from './LiveItemRow';

type Props = {
  data: LiveSourcePayload;
  isRefreshing: boolean;
  onRefresh: (sourceId: string) => void;
  onOpenItem: (item: LiveItem) => void;
};

export function LiveSourcePanel({ data, isRefreshing, onRefresh, onOpenItem }: Props) {
  const items = data.items?.slice(0, 6) || [];
  return (
    <section className="live-source-panel">
      <header className="live-source-header">
        <div className="live-source-title">
          <span>{data.icon || '•'}</span>
          <strong>{data.name || data.source_id}</strong>
        </div>
        <div className="live-source-controls">
          <span>Last updated: {data.updated_at ? new Date(data.updated_at).toLocaleTimeString() : '--:--:--'}</span>
          <button className="live-refresh-btn" onClick={() => onRefresh(data.source_id)}>
            Refresh
          </button>
          {isRefreshing ? <span className="tiny-spinner" aria-label="Refreshing" /> : null}
        </div>
      </header>

      {data.error ? <p className="live-error">{data.error}</p> : null}

      <div className="live-item-list">
        {items.length === 0 ? <p className="live-empty">No items yet.</p> : null}
        {items.map((item) => (
          <LiveItemRow key={item.id} item={item} onOpen={onOpenItem} />
        ))}
      </div>
    </section>
  );
}
