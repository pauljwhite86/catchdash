import { useEffect, useMemo, useState } from 'react';

import { getLiveSocial, refreshLiveSource } from '../app/api';
import type { LiveItem, LiveSocialResponse, LiveSource } from '../app/types';
import { LiveItemModal } from './LiveItemModal';
import { LiveSourcePanel } from './LiveSourcePanel';

export function LivePane() {
  const [livePlaying, setLivePlaying] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingAll, setIsRefreshingAll] = useState(false);
  const [refreshingSource, setRefreshingSource] = useState<Partial<Record<LiveSource, boolean>>>({});
  const [data, setData] = useState<LiveSocialResponse | null>(null);
  const [selectedItem, setSelectedItem] = useState<LiveItem | null>(null);
  const [isVisible, setIsVisible] = useState(document.visibilityState === 'visible');

  useEffect(() => {
    const onVisibility = () => {
      setIsVisible(document.visibilityState === 'visible');
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  const fetchAll = async () => {
    setIsRefreshingAll(true);
    try {
      const res = await getLiveSocial();
      setData(res);
    } finally {
      setIsRefreshingAll(false);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAll().catch(() => {
      setIsLoading(false);
      setIsRefreshingAll(false);
    });
  }, []);

  useEffect(() => {
    if (!livePlaying || !isVisible || selectedItem) {
      return;
    }
    const intervalMs = Math.max(5000, (data?.refresh_interval_seconds || 30) * 1000);
    const id = window.setInterval(() => {
      fetchAll().catch(() => {});
    }, intervalMs);
    return () => clearInterval(id);
  }, [livePlaying, isVisible, selectedItem, data?.refresh_interval_seconds]);

  const onRefreshSource = async (source: LiveSource) => {
    setRefreshingSource((prev) => ({ ...prev, [source]: true }));
    try {
      const res = await refreshLiveSource(source);
      setData((prev) => {
        if (!prev) {
          return {
            updated_at: new Date().toISOString(),
            refresh_interval_seconds: 30,
            items: [...res.items].sort((a, b) => dateTs(b.timestamp) - dateTs(a.timestamp)),
            sources: [res],
          };
        }
        const nextSources = prev.sources.map((row) => (row.source_id === source ? res : row));
        const nextItems = nextSources
          .flatMap((row) => row.items || [])
          .sort((a, b) => dateTs(b.timestamp) - dateTs(a.timestamp));
        return {
          ...prev,
          updated_at: new Date().toISOString(),
          items: nextItems,
          sources: nextSources,
        };
      });
    } finally {
      setRefreshingSource((prev) => ({ ...prev, [source]: false }));
    }
  };

  const sourceData = useMemo(() => data?.sources || [], [data]);
  const mergedItems = useMemo(() => data?.items || [], [data]);

  return (
    <div className="live-pane">
      <header className="live-pane-header">
        <h2>Live</h2>
        <div className="live-pane-controls">
          <button onClick={() => setLivePlaying((x) => !x)}>
            Live: {livePlaying ? 'Playing' : 'Paused'}
          </button>
          {isRefreshingAll ? <span className="tiny-spinner" aria-label="Refreshing all" /> : null}
        </div>
      </header>

      {isLoading ? (
        <section className="live-skeletons">
          {Array.from({ length: 4 }).map((_, idx) => (
            <article key={idx} className="live-source-panel skeleton-card">
              <div className="skeleton-line w-55" />
              <div className="skeleton-line w-80" />
              <div className="skeleton-line w-70" />
            </article>
          ))}
        </section>
      ) : (
        <>
          <section className="live-merged">
            <h3>Latest Across Sources</h3>
            <div className="live-item-list">
              {mergedItems.slice(0, 8).map((item) => (
                <button key={item.id} className="live-item-row" onClick={() => setSelectedItem(item)}>
                  <strong>{item.title || item.text.slice(0, 80) || 'Untitled'}</strong>
                  <span>
                    {formatRelativeTime(item.timestamp)} • {item.source}
                  </span>
                </button>
              ))}
            </div>
          </section>
          <section className="live-panels">
            {sourceData.map((source) => (
            <LiveSourcePanel
              key={source.source_id}
              data={source}
              isRefreshing={!!refreshingSource[source.source_id]}
              onRefresh={onRefreshSource}
              onOpenItem={setSelectedItem}
            />
            ))}
          </section>
        </>
      )}

      {selectedItem ? <LiveItemModal item={selectedItem} onClose={() => setSelectedItem(null)} /> : null}
    </div>
  );
}

function dateTs(value: string): number {
  const ts = Date.parse(value);
  return Number.isNaN(ts) ? 0 : ts;
}

function formatRelativeTime(value: string): string {
  const now = Date.now();
  const target = Date.parse(value);
  if (Number.isNaN(target)) {
    return 'Unknown';
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
  return `${Math.floor(diffHours / 24)}d ago`;
}
