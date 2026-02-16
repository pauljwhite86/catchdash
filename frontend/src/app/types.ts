export type Topic = {
  topic_id: string;
  name: string;
  icon?: string | null;
};

export type TopicItem = {
  item_id: string;
  title: string;
  url: string;
  source_name?: string;
  summary?: string | null;
  published_at?: string | null;
  image_url?: string | null;
};

export type LiveSource = string;

export type LiveMedia = {
  type: 'image';
  url: string;
};

export type LiveItem = {
  id: string;
  source: LiveSource;
  topic: string;
  timestamp: string;
  title: string;
  text: string;
  author: string;
  url: string;
  media: LiveMedia[];
};

export type LiveSourcePayload = {
  source_id: LiveSource;
  name: string;
  icon: string;
  updated_at: string;
  items: LiveItem[];
  error?: string | null;
};

export type LiveSocialResponse = {
  updated_at: string;
  refresh_interval_seconds?: number;
  items: LiveItem[];
  sources: LiveSourcePayload[];
};
