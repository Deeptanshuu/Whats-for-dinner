// Strip emoji and flag characters, then tidy the spaces left behind.
export function removeEmojis(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/\p{Extended_Pictographic}|[\u{1F1E6}-\u{1F1FF}]|️|‍/gu, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Minutes as text, e.g. 45 -> "45 min", 90 -> "1 h 30 min". Empty when unknown.
export function formatMinutes(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '';
  if (value < 60) return `${value} min`;
  const h = Math.floor(value / 60);
  const m = value % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
