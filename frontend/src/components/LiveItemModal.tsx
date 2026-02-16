import type { LiveItem } from '../app/types';

type Props = {
  item: LiveItem;
  onClose: () => void;
};

export function LiveItemModal({ item, onClose }: Props) {
  return (
    <div className="overlay" onClick={onClose}>
      <section className="overlay-card live-item-modal" onClick={(e) => e.stopPropagation()}>
        <header className="live-item-modal-header">
          <h3>{item.title || 'Live item'}</h3>
          <button onClick={onClose}>Close</button>
        </header>

        <div className="live-item-modal-meta">
          <span>{item.source}</span>
          <span>{new Date(item.timestamp).toLocaleString()}</span>
          <span>{item.author || item.topic}</span>
        </div>

        {item.text ? <p className="live-item-modal-text">{item.text}</p> : null}

        {item.media?.length ? (
          <div className="live-item-modal-media">
            {item.media.map((m, idx) => (
              <img key={`${item.id}-${idx}`} src={m.url} alt="" />
            ))}
          </div>
        ) : null}

        <a className="big-open-btn" href={item.url} target="_blank" rel="noreferrer">
          Open in new tab
        </a>
      </section>
    </div>
  );
}
