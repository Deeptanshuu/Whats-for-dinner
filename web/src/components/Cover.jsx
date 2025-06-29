/* eslint-disable react/prop-types */
import { useMemo } from 'react';
import { coverSvg, grainUrl } from '../cover/plate';

// Drawn covers are kept by recipe id and shape, so a card that comes back
// (paging, going back from a recipe) costs nothing to show again.
const cache = new Map();
const LIMIT = 300;

// The paper grain is one small generated image. It is set once as a CSS variable
// on the page, so every cover shares it (see .cover-grain in index.css).
let grainSet = false;
function shareGrain() {
  if (grainSet || typeof document === 'undefined') return;
  grainSet = true;
  const url = grainUrl();
  if (url) document.documentElement.style.setProperty('--cover-grain', url);
}

function drawn(recipe, aspect) {
  const count = Array.isArray(recipe.palette) ? recipe.palette.length : 0;
  const key = `${recipe.id}:${aspect}:${count}`;
  let hit = cache.get(key);
  if (!hit) {
    hit = coverSvg(recipe, aspect);
    if (cache.size >= LIMIT) cache.delete(cache.keys().next().value);
    cache.set(key, hit);
  }
  return hit;
}

// The recipe's cover: an abstract plate drawn from its main ingredients. It
// stands where a photo would. `recipe` needs id, title (or name), cuisine,
// course and palette; `aspect` is width over height. The box keeps that
// shape before and after drawing, so nothing around it moves.
const Cover = ({ recipe, aspect = 1.5, className = '' }) => {
  shareGrain();
  const { viewBox, body } = useMemo(() => drawn(recipe, aspect), [recipe, aspect]);
  const names = (Array.isArray(recipe.palette) ? recipe.palette : []).map((p) => p && p.name).filter(Boolean);
  const label = names.length
    ? `Illustration of a dish made with ${names.join(', ')}`
    : 'Illustration of a dish';
  return (
    <div
      role="img"
      aria-label={label}
      className={`relative overflow-hidden rounded-[3px] bg-[#e9e6de] ${className}`}
      style={{ aspectRatio: String(aspect) }}
    >
      <svg
        aria-hidden="true"
        viewBox={viewBox}
        preserveAspectRatio="xMidYMid slice"
        className="block h-full w-full"
        dangerouslySetInnerHTML={{ __html: body }}
      />
      {/* One shared paper grain over the flat colours. */}
      <span aria-hidden="true" className="cover-grain" />
    </div>
  );
};

export default Cover;
