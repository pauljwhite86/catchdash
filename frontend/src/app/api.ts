const BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8080';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getTopics() {
  return request<{ topics: Array<{ topic_id: string; name: string; icon?: string | null }> }>('/api/topics');
}

export function getTopicItems(topicId: string, force = false) {
  return request<{
    topic_id: string;
    topic_name: string;
    updated_at?: string;
    items: Array<{
      item_id: string;
      title: string;
      url: string;
      source_name?: string;
      summary?: string | null;
      published_at?: string | null;
      image_url?: string | null;
    }>;
  }>(
    `/api/topics/${topicId}/items?force=${force ? 'true' : 'false'}`
  );
}

export function enqueueTTS(topicId: string, itemId: string, type: 'tts_full_page' | 'tts_summary') {
  return request<{ id: string; status: string; progress: number; message?: string | null }>('/api/jobs', {
    method: 'POST',
    body: JSON.stringify({ type, topic_id: topicId, item_id: itemId }),
  });
}

export function getJob(jobId: string) {
  return request<{
    id: string;
    status: string;
    progress: number;
    message?: string | null;
    output_ref?: string | null;
  }>(`/api/jobs/${jobId}`);
}

export function listJobs() {
  return request<{
    jobs: Array<{
      id: string;
      type: string;
      topic_id: string;
      item_id: string;
      status: string;
      progress: number;
      message?: string | null;
      output_ref?: string | null;
      created_at?: string;
      updated_at?: string;
    }>;
  }>('/api/jobs');
}

export function getLiveSocial() {
  return request<{
    updated_at: string;
    refresh_interval_seconds?: number;
    items: Array<{
      id: string;
      source: string;
      topic: string;
      timestamp: string;
      title: string;
      text: string;
      author: string;
      url: string;
      media: Array<{ type: 'image'; url: string }>;
    }>;
    sources: Array<{
      source_id: string;
      name: string;
      icon: string;
      updated_at: string;
      items: Array<{
        id: string;
        source: string;
        topic: string;
        timestamp: string;
        title: string;
        text: string;
        author: string;
        url: string;
        media: Array<{ type: 'image'; url: string }>;
      }>;
      error?: string | null;
    }>;
  }>('/api/live/social');
}

export function refreshLiveSource(source: string) {
  return request<{
    source_id: string;
    name: string;
    icon: string;
    updated_at: string;
    items: Array<{
      id: string;
      source: string;
      topic: string;
      timestamp: string;
      title: string;
      text: string;
      author: string;
      url: string;
      media: Array<{ type: 'image'; url: string }>;
    }>;
    error?: string | null;
  }>(`/api/live/social/${source}/refresh`, { method: 'POST' });
}
