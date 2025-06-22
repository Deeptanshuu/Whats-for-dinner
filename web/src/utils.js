// Strip emoji and flag characters, then tidy the spaces left behind.
export function removeEmojis(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/\p{Extended_Pictographic}|[\u{1F1E6}-\u{1F1FF}]|️|‍/gu, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Recipe names in the data carry the word "Recipe"; drop it for display.
export function displayTitle(str) {
  if (typeof str !== 'string') return '';
  // Also inside: "Methi Chaman Recipe - Paneer In..."; separators become an en dash.
  const out = str
    .replace(/\s+recipe\b/gi, '')
    .replace(/\s+[-|]\s*/g, ' \u2013 ')
    .replace(/\s+/g, ' ')
    .trim();
  return out || str;
}

// Cuisine and course labels like "North Indian Recipes": drop the trailing word for display.
export function displayLabel(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/\s+recipes?\s*$/i, '').trim() || str;
}

// Minutes as text, e.g. 45 -> "45 min", 90 -> "1 h 30 min". Empty when unknown.
export function formatMinutes(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '';
  if (value < 60) return `${value} min`;
  const h = Math.floor(value / 60);
  const m = value % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
