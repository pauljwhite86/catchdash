import { ReactNode } from 'react';

type MobileView = 'audio' | 'live';

type Props = {
  left: ReactNode;
  right: ReactNode;
  mobileView: MobileView;
  onChangeMobileView: (view: MobileView) => void;
};

export function SplitLayout({ left, right, mobileView, onChangeMobileView }: Props) {
  return (
    <section className="split-layout">
      <div className="mobile-pane-toggle">
        <button className={mobileView === 'audio' ? 'active' : ''} onClick={() => onChangeMobileView('audio')}>
          Audio
        </button>
        <button className={mobileView === 'live' ? 'active' : ''} onClick={() => onChangeMobileView('live')}>
          Live
        </button>
      </div>

      <section className={`split-col left-col ${mobileView === 'audio' ? 'show-mobile' : ''}`}>{left}</section>
      <section className={`split-col right-col ${mobileView === 'live' ? 'show-mobile' : ''}`}>{right}</section>
    </section>
  );
}
