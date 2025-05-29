import { useState, useCallback } from 'react';

const KEY = 'recipesense:likes';

function read() {
  try {
    const raw = window.localStorage.getItem(KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list.filter((n) => Number.isInteger(n)) : [];
  } catch {
    return [];
  }
}

function write(list) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // Storage blocked or full: likes just last for this visit.
  }
}

// Liked recipe ids, kept in localStorage.
export default function useLikes() {
  const [liked, setLiked] = useState(read);

  const toggle = useCallback((id) => {
    setLiked((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      write(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    write([]);
    setLiked([]);
  }, []);

  return { liked, toggle, clear };
}
