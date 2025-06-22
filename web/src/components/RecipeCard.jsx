/* eslint-disable react/prop-types */
import { Link } from 'react-router-dom';
import LikeButton from './LikeButton';
import { formatMinutes, displayTitle, displayLabel } from '../utils';

// A text-only entry, like a line in a cookbook index. The whole card links to the recipe.
function RecipeCard({ recipe, liked, onToggleLike, newTab = false }) {
  const { id, title, total_time, veg, cuisine, course } = recipe;
  const time = formatMinutes(total_time);
  const meta = [cuisine, course].filter(Boolean).map(displayLabel).join(' · ');

  return (
    <article className="group relative flex h-full flex-col border-t border-slate-200 pb-6 pt-5">
      {meta && <p className="mb-2 pr-12 text-sm text-slate-500">{meta}</p>}
      <h3 className="pr-12 font-serif text-xl font-medium leading-snug text-ink">
        <Link
          to={`/recipe/${id}`}
          target={newTab ? '_blank' : undefined}
          rel={newTab ? 'noopener noreferrer' : undefined}
          className="line-clamp-3 decoration-slate-400 decoration-1 underline-offset-4 after:absolute after:inset-0 after:content-[''] group-hover:underline"
        >
          {displayTitle(title)}
        </Link>
      </h3>
      <div className="mt-auto flex items-center gap-4 pt-4 text-sm text-slate-600">
        {time && <span>{time}</span>}
        {veg && (
          <span className="inline-flex items-center gap-1.5 text-green-800">
            <span className="h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
            Veg
          </span>
        )}
      </div>
      <LikeButton liked={liked} onToggle={onToggleLike} className="absolute right-0 top-3 z-10 -mr-2.5" />
    </article>
  );
}

export default RecipeCard;
