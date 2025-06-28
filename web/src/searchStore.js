import { useState, useEffect } from 'react';

// The search screen's state, kept outside the component tree so it survives a
// visit to a recipe page, and mirrored to sessionStorage so it also survives a
// refresh. It is per tab and is dropped when the person presses Clear.
const KEY = 'recipesense:search';
// Kept when the search is cleared: the server's lists and how the panel is set up, not what was searched.
const KEEP = ['meta', 'mode', 'model', 'expanded'];

function read() {
  try {
    const data = JSON.parse(window.sessionStorage.getItem(KEY) || '{}');
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
  } catch {
    return {};
  }
}

let state = read();
let pending = false;

function flush() {
  pending = false;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Storage blocked or full: the state still lasts until the tab reloads.
  }
}

export function getStored(key, fallback) {
  return Object.prototype.hasOwnProperty.call(state, key) ? state[key] : fallback;
}

export function setStored(key, value) {
  if (state[key] === value) return;
  state = { ...state, [key]: value };
  if (!pending) {
    pending = true;
    queueMicrotask(flush);
  }
}

export function clearStored() {
  state = Object.fromEntries(KEEP.filter((k) => k in state).map((k) => [k, state[k]]));
  flush();
}

// useState whose value is read from the store on mount and written back on change.
export function useStored(key, initial) {
  const [value, setValue] = useState(() => getStored(key, initial));
  useEffect(() => {
    setStored(key, value);
  }, [key, value]);
  return [value, setValue];
}
