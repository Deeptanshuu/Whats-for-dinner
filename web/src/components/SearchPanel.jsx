/* eslint-disable react/prop-types */
import { useState, useMemo, useEffect, useLayoutEffect, useRef } from 'react';
import { X, Search, Plus } from 'lucide-react';
import VegToggle from './VegToggle';
import ModelPicker from './ModelPicker';
import Section from './Section';
import ingredientsData from '../ingredients.json';
import { removeEmojis } from '../utils';
import { useStored, getStored, setStored } from '../searchStore';

const INGREDIENTS = ingredientsData.ingredients.map((name, i) => ({ id: `ing_${i}`, name: removeEmojis(name) }));
// The list is ordered by how often an ingredient is used, so the first few are the useful defaults.
const DEFAULT_SHOWN = 24;
const MATCHES_SHOWN = 40;

const MODES = [
  { id: 'ingredients', label: 'By ingredients' },
  { id: 'describe', label: 'Describe it' },
];

const SearchPanel = ({
  meta,
  busy,
  hasResults,
  likedCount,
  onClearLikes,
  onSearch,
  onClear,
  className = '',
  preset,
}) => {
  const [mode, setMode] = useStored('mode', 'ingredients');
  const [model, setModel] = useStored('model', 'learned');
  const [isVeg, setIsVeg] = useStored('veg', false);
  const [query, setQuery] = useStored('query', '');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIngredients, setSelectedIngredients] = useStored('ingredients', []);
  const [customIngredients, setCustomIngredients] = useStored('custom', []);
  const [selectedCuisines, setSelectedCuisines] = useStored('cuisines', []);
  const [selectedCourse, setSelectedCourse] = useStored('course', '');
  const [expanded, setExpanded] = useStored('expanded', { ingredients: true, cuisines: true, courses: true, model: true });
  const [hint, setHint] = useState('');
  const scroller = useRef(null);

  // On desktop the panel scrolls on its own; put it back where it was.
  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollTop = getStored('panelScroll', 0);
  }, []);

  useEffect(() => {
    if (!preset) return;
    setMode('describe');
    setQuery(preset.query);
    setHint('');
    onSearch({ mode: 'describe', query: preset.query, veg: isVeg });
    // Runs once per picked example; the other values are read as they are at that moment.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset]);

  const toggleSection = (s) => setExpanded((p) => ({ ...p, [s]: !p[s] }));

  const term = searchTerm.trim().toLowerCase();

  const { shown, matchCount } = useMemo(() => {
    const selected = INGREDIENTS.filter((i) => selectedIngredients.includes(i.id));
    const rest = INGREDIENTS.filter((i) => !selectedIngredients.includes(i.id));
    if (term) {
      const matches = rest.filter((i) => i.name.toLowerCase().includes(term));
      return { shown: [...selected, ...matches.slice(0, MATCHES_SHOWN)], matchCount: matches.length };
    }
    return { shown: [...selected, ...rest.slice(0, DEFAULT_SHOWN)], matchCount: rest.length };
  }, [term, selectedIngredients]);

  const toggleIngredient = (id) => {
    setSelectedIngredients((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    setSearchTerm('');
  };

  const canAddCustom =
    searchTerm.trim() &&
    !INGREDIENTS.some((i) => i.name.toLowerCase() === term) &&
    !customIngredients.includes(searchTerm.trim());

  const addCustom = () => {
    if (!canAddCustom) return;
    setCustomIngredients([...customIngredients, searchTerm.trim()]);
    setSearchTerm('');
  };

  const toggleCuisine = (name) =>
    setSelectedCuisines((prev) => (prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name]));

  const run = (overrides = {}) => {
    const m = overrides.model || model;
    if (mode === 'describe') {
      if (!query.trim()) {
        setHint('Type what you feel like eating first.');
        return;
      }
      setHint('');
      onSearch({ mode, query: query.trim(), veg: isVeg });
      return;
    }
    setHint('');
    const ingredients = [
      ...INGREDIENTS.filter((i) => selectedIngredients.includes(i.id)).map((i) => i.name),
      ...customIngredients,
    ];
    onSearch({ mode, model: m, ingredients, cuisine: selectedCuisines, course: selectedCourse, veg: isVeg });
  };

  const changeModel = (id) => {
    setModel(id);
    // Re-run so the timing comparison shows up straight away.
    if (hasResults && mode === 'ingredients' && !busy) run({ model: id });
  };

  const clearAll = () => {
    setSelectedIngredients([]);
    setCustomIngredients([]);
    setSelectedCuisines([]);
    setSelectedCourse('');
    setSearchTerm('');
    setQuery('');
    setHint('');
    setIsVeg(false);
    onClear();
  };

  const ingredientCount = selectedIngredients.length + customIngredients.length;
  const countNote = (n) => (n ? `${n} selected` : '');

  return (
    <div className={`flex-col ${className}`}>
      <div
        ref={scroller}
        onScroll={(e) => setStored('panelScroll', e.currentTarget.scrollTop)}
        className="px-5 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:px-8"
      >
        <div role="tablist" aria-label="Search mode" className="grid grid-cols-2 gap-1 rounded-full bg-[#efede8] p-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={mode === m.id}
              onClick={() => { setMode(m.id); setHint(''); }}
              className={`min-h-11 rounded-full text-[15px] lg:min-h-10 transition-colors ${
                mode === m.id ? 'bg-white font-medium text-ink ring-1 ring-slate-200' : 'text-slate-600 hover:text-ink'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <label htmlFor="veg-toggle" className="label cursor-pointer">Vegetarian only</label>
          <VegToggle id="veg-toggle" value={isVeg} onChange={setIsVeg} />
        </div>

        {mode === 'describe' ? (
          <div className="mt-4 border-t border-slate-200 py-5">
            <label htmlFor="describe-input" className="label mb-3 block">
              Describe what you feel like eating
            </label>
            <textarea
              id="describe-input"
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!busy) run();
                }
              }}
              placeholder="e.g. something warm and creamy with mushrooms"
              className="field resize-none rounded-2xl py-3 leading-relaxed"
            />
            <p className="mt-3 text-sm leading-relaxed text-slate-500">
              The vegetarian switch applies. Cuisine and course filters are only used when searching by ingredients.
            </p>
          </div>
        ) : (
          <div className="mt-4">
            <Section
              title="Ingredients"
              note={countNote(ingredientCount)}
              open={expanded.ingredients}
              onToggle={() => toggleSection('ingredients')}
            >
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  type="text"
                  aria-label="Search ingredients"
                  placeholder="Search ingredients"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') addCustom(); }}
                  className="field h-12 rounded-full pl-10 lg:h-11"
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {customIngredients.map((name) => (
                  <button
                    key={`custom-${name}`}
                    type="button"
                    aria-pressed="true"
                    onClick={() => setCustomIngredients(customIngredients.filter((c) => c !== name))}
                    className="chip chip-on"
                  >
                    {name}
                    <X size={14} aria-hidden="true" />
                  </button>
                ))}
                {shown.map((ingredient) => {
                  const on = selectedIngredients.includes(ingredient.id);
                  return (
                    <button
                      key={ingredient.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleIngredient(ingredient.id)}
                      className={`chip ${on ? 'chip-on' : ''}`}
                    >
                      {ingredient.name}
                      {on && <X size={14} aria-hidden="true" />}
                    </button>
                  );
                })}
                {canAddCustom && (
                  <button type="button" onClick={addCustom} className="chip">
                    <Plus size={14} aria-hidden="true" />
                    Add &ldquo;{searchTerm.trim()}&rdquo;
                  </button>
                )}
              </div>
              <p className="mt-3 text-sm text-slate-500">
                {term
                  ? matchCount > MATCHES_SHOWN
                    ? `Showing ${MATCHES_SHOWN} of ${matchCount} matches.`
                    : matchCount === 0
                      ? 'No listed ingredient matches. Press Enter to add it as your own.'
                      : ''
                  : 'The most used ingredients. Search to find others.'}
              </p>
            </Section>

            <Section
              title="Cuisine"
              note={countNote(selectedCuisines.length)}
              open={expanded.cuisines}
              onToggle={() => toggleSection('cuisines')}
            >
              <div className="flex flex-wrap gap-2">
                {meta.cuisines.map((c) => {
                  const on = selectedCuisines.includes(c.name);
                  return (
                    <button key={c.name} type="button" aria-pressed={on} onClick={() => toggleCuisine(c.name)} className={`chip ${on ? 'chip-on' : ''}`}>
                      {c.name}
                    </button>
                  );
                })}
              </div>
            </Section>

            <Section
              title="Course"
              note={selectedCourse}
              open={expanded.courses}
              onToggle={() => toggleSection('courses')}
            >
              <div role="radiogroup" aria-label="Course" className="flex flex-wrap gap-2">
                {meta.courses.map((c) => {
                  const on = selectedCourse === c.name;
                  return (
                    <button
                      key={c.name}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      onClick={() => setSelectedCourse(on ? '' : c.name)}
                      className={`chip ${on ? 'chip-on' : ''}`}
                    >
                      {c.name}
                    </button>
                  );
                })}
              </div>
            </Section>

            <div className="border-t border-slate-200 py-5">
              <ModelPicker models={meta.models} value={model} onChange={changeModel} />
            </div>

            {meta.status === 'loading' && <p className="pb-4 text-sm text-slate-500">Loading cuisines and courses...</p>}
            {meta.status === 'fallback' && (
              <p className="pb-4 text-sm leading-relaxed text-slate-500">
                Could not load the full lists from the server. Showing a short default list.
              </p>
            )}

            {likedCount > 0 && (
              <div className="flex items-center justify-between gap-3 border-t border-slate-200 py-4">
                <p className="text-[15px] text-slate-600">
                  Tuned to your likes ({likedCount} liked)
                </p>
                <button type="button" onClick={onClearLikes} className="min-h-11 text-[15px] text-red-700 underline-offset-4 hover:underline lg:min-h-9">
                  Clear likes
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="sticky bottom-0 z-20 border-t border-slate-200 bg-paper px-5 py-3 lg:static lg:px-8 lg:py-4">
        {hint && <p className="mb-2 text-sm text-red-700" role="alert">{hint}</p>}
        <div className="flex items-center gap-3">
          <button type="button" disabled={busy} className="btn-primary flex-1" onClick={() => run()}>
            {busy ? 'Finding recipes...' : 'Find recipes'}
          </button>
          <button
            type="button"
            className="min-h-12 rounded-full px-4 text-[15px] text-red-700 transition-colors hover:bg-red-50"
            onClick={clearAll}
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
};

export default SearchPanel;
