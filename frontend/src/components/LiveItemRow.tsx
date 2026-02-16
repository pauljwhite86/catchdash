import type { LiveItem } from '../app/types';

type Props = {
  item: LiveItem;
  onOpen: (item: LiveItem) => void;
};

export function LiveItemRow({ item, onOpen }: Props) {
  const title = item.title || item.text.slice(0, 80) || 'Untitled';
  return (
    <button className="live-item-row" onClick={() => onOpen(item)}>
      <strong>{title}</strong>
      <span>
        {formatRelativeTime(item.timestamp)} • {item.author || item.topic}
      </span>
    </button>
  );
}

function formatRelativeTime(value: string): string {
  const now = Date.now();
  const target = new Date(value).getTime();
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
