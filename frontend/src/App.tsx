import { useEffect, useRef, useState } from 'react';

import { enqueueTTS, getJob, getTopicItems, getTopics, listJobs } from './app/api';
import type { Topic, TopicItem } from './app/types';
import { AudioPane } from './components/AudioPane';
import { LivePane } from './components/LivePane';
import { SplitLayout } from './components/SplitLayout';

type ItemTTSState = {
  jobId: string;
  status: string;
  progress: number;
  message?: string | null;
  outputRef?: string | null;
};

type MobileView = 'audio' | 'live';

export function App() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>('');
  const [selectedTopicName, setSelectedTopicName] = useState<string>('');
  const [items, setItems] = useState<TopicItem[]>([]);
  const [isLoadingItems, setIsLoadingItems] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [ttsByKey, setTtsByKey] = useState<Record<string, ItemTTSState>>({});
  const [ttsModeByItem, setTtsModeByItem] = useState<Record<string, 'tts_full_page' | 'tts_summary'>>({});
  const [playingItemKey, setPlayingItemKey] = useState<string | null>(null);
  const [currentTrackTitle, setCurrentTrackTitle] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<MobileView>('audio');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const wakeLockRef = useRef<any>(null);

  const keyFor = (topicId: string, itemId: string) => `${topicId}:${itemId}`;

  const ttsByItemForSelected: Record<string, ItemTTSState> = {};
  for (const item of items) {
    const state = ttsByKey[keyFor(selectedTopicId, item.item_id)];
    if (state) {
      ttsByItemForSelected[item.item_id] = state;
    }
  }
  const playingItemIdForSelected =
    playingItemKey && selectedTopicId && playingItemKey.startsWith(`${selectedTopicId}:`)
      ? playingItemKey.slice(selectedTopicId.length + 1)
      : null;

  useEffect(() => {
    getTopics()
      .then((res) => {
        setTopics(res.topics);
        if (res.topics.length > 0) {
          setSelectedTopicId(res.topics[0].topic_id);
          setSelectedTopicName(res.topics[0].name);
        }
      })
      .catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    if (!selectedTopicId) {
      return;
    }
    setIsLoadingItems(true);
    setItems([]);
    setTtsModeByItem({});
    getTopicItems(selectedTopicId)
      .then(async (res) => {
        setItems(res.items);
        setSelectedTopicName(res.topic_name);
        try {
          const jobsRes = await listJobs();
          const itemIds = new Set(res.items.map((item) => item.item_id));
          const relevant = jobsRes.jobs.filter(
            (job) => job.topic_id === selectedTopicId && itemIds.has(job.item_id)
          );
          const latestByKey: Record<string, typeof relevant[number]> = {};
          for (const job of relevant) {
            const k = keyFor(job.topic_id, job.item_id);
            const prev = latestByKey[k];
            const jobTs = Date.parse(job.updated_at || job.created_at || '1970-01-01T00:00:00Z');
            const prevTs = prev ? Date.parse(prev.updated_at || prev.created_at || '1970-01-01T00:00:00Z') : -1;
            if (!prev || jobTs >= prevTs) {
              latestByKey[k] = job;
            }
          }
          setTtsByKey((prev) => {
            const next = { ...prev };
            for (const [k, job] of Object.entries(latestByKey)) {
              next[k] = {
                jobId: job.id,
                status: job.status,
                progress: job.progress,
                message: job.message || null,
                outputRef: job.output_ref || null,
              };
            }
            return next;
          });
        } catch {
          // Ignore hydration failures and keep local state.
        }
      })
      .catch((err) => setError(String(err)))
      .finally(() => setIsLoadingItems(false));
  }, [selectedTopicId]);

  useEffect(() => {
    const activeEntries = Object.entries(ttsByKey).filter(([, row]) => row.status === 'queued' || row.status === 'processing');
    if (activeEntries.length === 0) {
      return;
    }
    const id = setInterval(async () => {
      const updates = await Promise.all(
        activeEntries.map(async ([itemId, state]) => {
          try {
            const job = await getJob(state.jobId);
            return [
              itemId,
              {
                ...state,
                status: job.status,
                progress: job.progress,
                message: job.message,
                outputRef: job.output_ref ?? state.outputRef ?? null,
              },
            ] as const;
          } catch {
            return [itemId, state] as const;
          }
        })
      );
      setTtsByKey((prev) => {
        const next = { ...prev };
        for (const [itemKey, row] of updates) {
          next[itemKey] = row;
        }
        return next;
      });
    }, 1200);
    return () => clearInterval(id);
  }, [ttsByKey]);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const requestWakeLock = async () => {
      if (cancelled || document.visibilityState !== 'visible') {
        return;
      }
      try {
        const nav = navigator as Navigator & {
          wakeLock?: { request: (type: 'screen') => Promise<any> };
        };
        if (!nav.wakeLock?.request) {
          return;
        }
        wakeLockRef.current = await nav.wakeLock.request('screen');
      } catch {
        // Best effort only.
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        requestWakeLock().catch(() => {});
      }
    };

    requestWakeLock().catch(() => {});
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', onVisibilityChange);
      if (wakeLockRef.current) {
        wakeLockRef.current.release?.().catch?.(() => {});
        wakeLockRef.current = null;
      }
    };
  }, []);

  const onQueueTTS = async (itemId: string, mode: 'tts_full_page' | 'tts_summary') => {
    const job = await enqueueTTS(selectedTopicId, itemId, mode);
    const itemKey = keyFor(selectedTopicId, itemId);
    setTtsByKey((prev) => ({
      ...prev,
      [itemKey]: {
        jobId: job.id,
        status: job.status,
        progress: job.progress,
        message: job.message,
        outputRef: null,
      },
    }));
  };

  const onPlayPause = async (item: TopicItem, row: ItemTTSState) => {
    if (!row.outputRef) {
      return;
    }
    const backendBase = (import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8080').replace(/\/$/, '');
    const audioUrl = row.outputRef.startsWith('http') ? row.outputRef : `${backendBase}${row.outputRef}`;

    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.addEventListener('ended', () => setPlayingItemKey(null));
    }
    const player = audioRef.current;
    const itemKey = keyFor(selectedTopicId, item.item_id);
    if (playingItemKey === itemKey) {
      player.pause();
      setPlayingItemKey(null);
      return;
    }
    if (player.src !== audioUrl) {
      player.src = audioUrl;
    }
    await player.play();
    setPlayingItemKey(itemKey);
    setCurrentTrackTitle(item.title);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>Catchdash</h1>
        <p>Audio + Live workspace</p>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <section className="workspace">
        <SplitLayout
          mobileView={mobileView}
          onChangeMobileView={setMobileView}
          left={
            <AudioPane
              topics={topics}
              selectedTopicId={selectedTopicId}
              selectedTopicName={selectedTopicName}
              items={items}
              isLoadingItems={isLoadingItems}
              ttsByItem={ttsByItemForSelected}
              ttsModeByItem={ttsModeByItem}
              playingItemId={playingItemIdForSelected}
              onSelectTopic={setSelectedTopicId}
              onSetMode={(itemId, mode) => setTtsModeByItem((prev) => ({ ...prev, [itemId]: mode }))}
              onQueueTTS={onQueueTTS}
              onPlayPause={onPlayPause}
            />
          }
          right={<LivePane />}
        />
      </section>

      <footer className="player-dock">
        <div className="player-left">
          <strong>Player</strong>
          <span>{currentTrackTitle || 'No track selected'}</span>
        </div>
        <div className="player-controls">
          <button
            onClick={async () => {
              if (!audioRef.current || !audioRef.current.src) {
                return;
              }
              await audioRef.current.play();
            }}
          >
            Play
          </button>
          <button
            onClick={() => {
              if (!audioRef.current) {
                return;
              }
              audioRef.current.pause();
              setPlayingItemKey(null);
            }}
          >
            Pause
          </button>
        </div>
      </footer>
    </main>
  );
}
