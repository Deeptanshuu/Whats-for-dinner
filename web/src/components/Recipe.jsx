/* eslint-disable react/prop-types */
import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Loading from './Loading';
import LikeButton from './LikeButton';
import RecipeCard from './RecipeCard';
import Cover from './Cover';
import Wordmark from './Wordmark';
import useLikes from '../useLikes';
import { getRecipe, getSimilar } from '../api';
import { formatMinutes, displayTitle, displayLabel } from '../utils';

const toList = (value, sep) => {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string') return value.split(sep).map((s) => s.trim()).filter(Boolean);
  return [];
};

// The source text runs sentences together; group them two at a time into steps.
const sentence = (s) => (/[.!?]$/.test(s) ? s : `${s}.`);
const formatInstructions = (instructions) => {
  const steps = toList(instructions, '.').filter((step) => step !== '|');
  const out = [];
  for (let i = 0; i < steps.length; i += 2) {
    out.push([steps[i], steps[i + 1]].filter(Boolean).map(sentence).join(' '));
  }
  return out;
};

// `back` is how many history steps lead back to the results this visit started from.
// With it the link goes back in history, so the results are exactly as they were left;
// without it (a direct visit) it is a plain link to the search screen.
const Page = ({ children }) => {
  const navigate = useNavigate();
  const back = Number(useLocation().state?.back) || 0;
  const goBack = (e) => {
    if (!back || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(-back);
  };
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-5xl flex-col items-start px-5 pb-2 pt-6 lg:px-8">
        <Wordmark />
        <Link
          to="/"
          onClick={goBack}
          className="-ml-0.5 mt-3 inline-flex min-h-11 items-center gap-1.5 text-[15px] text-slate-600 underline-offset-4 hover:text-ink hover:underline"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          {back ? 'Back to results' : 'Back to search'}
        </Link>
      </header>
      {children}
    </div>
  );
};

const Fact = ({ label, value, veg }) => (
  <div className="min-w-0">
    <dt className="text-sm text-slate-500">{label}</dt>
    <dd className={`mt-0.5 flex items-center gap-1.5 text-base ${veg ? 'text-green-800' : 'text-ink'}`}>
      {veg && <span className="h-2 w-2 shrink-0 rounded-full bg-accent" aria-hidden="true" />}
      {value}
    </dd>
  </div>
);

const Recipe = () => {
  const { id } = useParams();
  const [state, setState] = useState({ status: 'loading', recipe: null, error: '' });
  const [similar, setSimilar] = useState({ status: 'loading', items: [], error: '' });
  const [attempt, setAttempt] = useState(0);
  const { liked, toggle } = useLikes();
  const numericId = Number(id);
  const back = Number(useLocation().state?.back) || 0;

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading', recipe: null, error: '' });
    setSimilar({ status: 'loading', items: [], error: '' });

    getRecipe(id, { signal: controller.signal })
      .then((recipe) => setState({ status: 'done', recipe, error: '' }))
      .catch((err) => {
        if (err.name !== 'AbortError') setState({ status: 'error', recipe: null, error: err.message, notFound: err.status === 404 });
      });

    getSimilar(id, { signal: controller.signal })
      .then((data) => setSimilar({ status: 'done', items: (data.recommendations || []).slice(0, 6), error: '' }))
      .catch((err) => {
        if (err.name !== 'AbortError') setSimilar({ status: 'error', items: [], error: err.message });
      });

    return () => controller.abort();
  }, [id, attempt]);

  useEffect(() => {
    if (state.status === 'done') document.title = `${displayTitle(state.recipe.name)} - RecipeSense`;
    return () => { document.title = 'RecipeSense'; };
  }, [state]);

  if (state.status === 'loading') {
    return <Page><div className="py-24"><Loading label="Loading recipe" /></div></Page>;
  }

  if (state.status === 'error') {
    return (
      <Page>
        <div className="mx-auto max-w-5xl px-5 py-16 lg:px-8">
          <h1 className="font-serif text-[28px] font-medium text-ink">
            {state.notFound ? 'Recipe not found' : 'Something went wrong'}
          </h1>
          <p className={`mt-3 text-base ${state.notFound ? 'text-slate-600' : 'text-red-700'}`} role="alert">
            {state.notFound ? 'That recipe may have been removed.' : state.error}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            {!state.notFound && (
              <button type="button" onClick={() => setAttempt((n) => n + 1)} className="btn-primary">
                Try again
              </button>
            )}
            <Link to="/" className="btn-quiet min-h-12">Back to search</Link>
          </div>
        </div>
      </Page>
    );
  }

  const { recipe } = state;
  const ingredients = toList(recipe.cooking_ingredients, ',');
  const steps = formatInstructions(recipe.cooking_instruction);
  const palette = Array.isArray(recipe.palette) ? recipe.palette : [];
  // One colour per ingredient line, when the server sent a list that lines up.
  const colors = Array.isArray(recipe.ingredient_colors) && recipe.ingredient_colors.length === ingredients.length
    ? recipe.ingredient_colors
    : [];
  const facts = [
    ['Prep', formatMinutes(recipe.prep_time)],
    ['Cook', formatMinutes(recipe.cook_time)],
    ['Total', formatMinutes(recipe.total_time)],
    ['Course', displayLabel(recipe.course)],
    ['Cuisine', displayLabel(recipe.cuisine)],
    ['Diet', recipe.veg ? 'Vegetarian' : 'Non-vegetarian'],
  ].filter(([, v]) => v);

  return (
    <Page>
      <article className="mx-auto max-w-5xl px-5 pb-16 pt-2 lg:px-8">
        {/* The cover as a banner: edge to edge and 2:1 on a phone, wider and so lower on a desktop. */}
        <Cover recipe={{ ...recipe, id: numericId, title: recipe.name }} aspect={2} className="-mx-5 rounded-none sm:mx-0 sm:rounded-[3px] lg:hidden" />
        <Cover recipe={{ ...recipe, id: numericId, title: recipe.name }} aspect={3} className="hidden lg:block" />
        <div className="max-w-3xl pt-7 lg:pt-9">
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-serif text-[28px] font-medium leading-tight tracking-[-0.01em] text-ink lg:text-[32px]">
            {displayTitle(recipe.name)}
          </h1>
          <LikeButton liked={liked.includes(numericId)} onToggle={() => toggle(numericId)} className="-mr-2.5 mt-0.5 shrink-0 lg:mt-2" />
        </div>
        {recipe.description && (
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-slate-600">{recipe.description}</p>
        )}

        <dl className="mt-8 grid grid-cols-3 gap-x-6 gap-y-5 border-y border-slate-200 py-5 sm:grid-cols-6">
          {facts.map(([label, value]) => (
            <Fact key={label} label={label} value={value} veg={label === 'Diet' && recipe.veg} />
          ))}
        </dl>

        {palette.length > 0 && (
          <div className="border-b border-slate-200 py-5">
            <p id="cover-legend" className="text-sm text-slate-500">The cover is drawn from the main ingredients</p>
            <ul aria-labelledby="cover-legend" className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
              {palette.map((p) => (
                <li key={p.name} className="flex min-w-0 items-start gap-2.5 text-[15px] leading-5 text-slate-700">
                  <span className="mt-1 h-3 w-3 shrink-0 rounded-full ring-1 ring-inset ring-ink/10" style={{ backgroundColor: p.color }} aria-hidden="true" />
                  <span className="line-clamp-2 min-w-0 break-words">{p.name}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <section className="mt-12">
          <h2 className="font-serif text-2xl font-medium text-ink">Ingredients</h2>
          <ul className="mt-4 grid grid-cols-1 gap-x-10 sm:grid-cols-2">
            {ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-center gap-3 border-b border-slate-100 py-2.5 text-base text-slate-800">
                {colors.length > 0 && (
                  <span
                    className={`h-2.5 w-2.5 shrink-0 rounded-[2px] ${colors[index] ? 'ring-1 ring-inset ring-ink/10' : ''}`}
                    style={colors[index] ? { backgroundColor: colors[index] } : undefined}
                    aria-hidden="true"
                  />
                )}
                {ingredient}
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-2xl font-medium text-ink">Method</h2>
          <ol className="mt-5 space-y-6">
            {steps.map((text, i) => (
              <li key={i} className="flex gap-5">
                <span className="w-6 shrink-0 pt-px text-right font-serif text-lg leading-relaxed text-slate-500">{i + 1}</span>
                <p className="max-w-[62ch] text-base leading-relaxed text-slate-800 lg:text-[17px]">{text}</p>
              </li>
            ))}
          </ol>
        </section>
        </div>
      </article>

      <section className="mx-auto max-w-5xl px-5 pb-16 lg:px-8">
        <h2 className="pb-2 font-serif text-2xl font-medium text-ink">More like this</h2>
        {similar.status === 'loading' && <Loading label="Finding similar recipes" />}
        {similar.status === 'error' && (
          <p className="py-6 text-base text-red-700" role="alert">Could not load similar recipes. {similar.error}</p>
        )}
        {similar.status === 'done' && similar.items.length === 0 && (
          <p className="py-6 text-base text-slate-600">No similar recipes found.</p>
        )}
        {similar.items.length > 0 && (
          <div className="grid grid-cols-1 gap-x-8 gap-y-10 border-t border-slate-200 pt-6 sm:grid-cols-2 lg:grid-cols-3">
            {similar.items.map((r) => (
              <RecipeCard key={r.id} recipe={r} back={back ? back + 1 : 0} liked={liked.includes(r.id)} onToggleLike={() => toggle(r.id)} />
            ))}
          </div>
        )}
      </section>
    </Page>
  );
};

export default Recipe;
