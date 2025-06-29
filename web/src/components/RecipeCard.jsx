/* eslint-disable react/prop-types */
import { Link } from 'react-router-dom';
import LikeButton from './LikeButton';
import Cover from './Cover';
import { formatMinutes, displayTitle, displayLabel } from '../utils';

// A card like a page in a cookbook: the drawn cover, then the words.
// The whole card links to the recipe. `back` is how many history steps lead back to the results.
function RecipeCard({ recipe, liked, onToggleLike, back = 1 }) {
  const { id, title, total_time, veg, cuisine, course } = recipe;
  const time = formatMinutes(total_time);
  const meta = [cuisine, course].filter(Boolean).map(displayLabel).join(' \u00b7 ');

  return (
    <article className="group relative flex h-full flex-col">
      <Cover recipe={recipe} aspect={1.5} />
      <div className="mt-2 flex min-h-11 items-center justify-between gap-3">
        <p className="min-w-0 truncate text-sm text-slate-500">{meta}</p>
        <LikeButton liked={liked} onToggle={onToggleLike} className="relative z-10 -mr-2.5 shrink-0" />
      </div>
      <h3 className="font-serif text-xl font-medium leading-snug text-ink">
        <Link
          to={`/recipe/${id}`}
          state={back ? { back } : undefined}
          className="line-clamp-3 decoration-slate-400 decoration-1 underline-offset-4 after:absolute after:inset-0 after:content-[''] group-hover:underline"
        >
          {displayTitle(title)}
        </Link>
      </h3>
      <div className="mt-auto flex items-center gap-4 pt-2.5 text-sm text-slate-600">
        {time && <span>{time}</span>}
        {veg && (
          <span className="inline-flex items-center gap-1.5 text-green-800">
            <span className="h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
            Veg
          </span>
        )}
      </div>
    </article>
  );
}

export default RecipeCard;
