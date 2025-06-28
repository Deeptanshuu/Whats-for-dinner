import { useEffect, useLayoutEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

// Scroll positions per history entry. Going back or forward returns to where
// the person was; opening a new page starts at the top. Kept in sessionStorage
// so it also works after a refresh.
const KEY = 'recipesense:scroll';

function read() {
  try {
    const data = JSON.parse(window.sessionStorage.getItem(KEY) || '{}');
    return data && typeof data === 'object' ? data : {};
  } catch {
    return {};
  }
}

const positions = read();

function remember(key, y) {
  positions[key] = Math.round(y);
  const keys = Object.keys(positions);
  if (keys.length > 60) delete positions[keys[0]];
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(positions));
  } catch {
    // Not stored: positions still last until the tab reloads.
  }
}

const ScrollManager = () => {
  const { key } = useLocation();
  const type = useNavigationType();

  useEffect(() => {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';
  }, []);

  useLayoutEffect(() => {
    const target = type === 'POP' ? positions[key] || 0 : 0;
    let frame = 0;
    let tries = 0;
    let restoring = true;
    let last = target;
    let timer = 0;

    // The page may still be loading its content or its fonts, so keep trying
    // for a moment until it is tall enough, and stop as soon as the person scrolls.
    const go = () => {
      if (!restoring) return;
      window.scrollTo(0, target);
      tries += 1;
      if (Math.abs(window.scrollY - target) > 1 && tries < 240) frame = requestAnimationFrame(go);
      else restoring = false;
    };
    go();
    // Web fonts change line breaks and so heights; settle once more when they are in.
    if (target > 0 && document.fonts && document.fonts.status !== 'loaded') {
      restoring = true;
      document.fonts.ready.then(() => {
        if (!restoring) return;
        tries = 0;
        go();
      });
    }

    const stop = () => {
      cancelAnimationFrame(frame);
      restoring = false;
    };
    const onScroll = () => {
      if (restoring) return;
      last = window.scrollY;
      clearTimeout(timer);
      timer = setTimeout(() => remember(key, last), 80);
    };
    const save = () => remember(key, last);

    window.addEventListener('wheel', stop, { passive: true });
    window.addEventListener('touchstart', stop, { passive: true });
    window.addEventListener('keydown', stop);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pagehide', save);
    return () => {
      // The position as last seen, not as it is now: the next page may already be in place.
      cancelAnimationFrame(frame);
      clearTimeout(timer);
      restoring = false;
      save();
      window.removeEventListener('wheel', stop);
      window.removeEventListener('touchstart', stop);
      window.removeEventListener('keydown', stop);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pagehide', save);
    };
  }, [key, type]);

  return null;
};

export default ScrollManager;
