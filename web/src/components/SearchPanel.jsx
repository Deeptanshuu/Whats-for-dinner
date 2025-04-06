/* eslint-disable react/prop-types */
import { useState, useMemo } from 'react';
import { X, Search } from 'lucide-react';
import VegToggle from './VegToggle';
import ModelPicker from './ModelPicker';
import Section from './Section';
import ingredientsData from '../ingredients.json';
import { removeEmojis } from '../utils';

const INGREDIENTS = ingredientsData.ingredients.map((name, i) => ({ id: `ing_${i}`, name }));

const chip = (on) =>
  `px-3 py-1 border-2 border-slate-500 rounded-full text-m font-medium transition duration-200 ${
    on ? 'bg-stone-700 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
  }`;

const MODES = [
  { id: 'ingredients', label: 'By ingredients' },
  { id: 'describe', label: 'Describe it' },
];

const SearchPanel = ({
  visible,
  onClose,
  meta,
  busy,
  hasResults,
  likedCount,
  onClearLikes,
  onSearch,
  onClear,
}) => {
  const [mode, setMode] = useState('ingredients');
  const [model, setModel] = useState('learned');
  const [isVeg, setIsVeg] = useState(false);
  const [query, setQuery] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [customIngredients, setCustomIngredients] = useState([]);
  const [selectedCuisines, setSelectedCuisines] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [expanded, setExpanded] = useState({ ingredients: true, cuisines: true, courses: true });
  const [hint, setHint] = useState('');

  const toggleSection = (s) => setExpanded((p) => ({ ...p, [s]: !p[s] }));

  const displayedIngredients = useMemo(() => {
    const term = searchTerm.toLowerCase();
    const list = term ? INGREDIENTS.filter((i) => i.name.toLowerCase().includes(term)) : [...INGREDIENTS];
    // Selected ones float to the top.
    return list.sort((a, b) => Number(selectedIngredients.includes(b.id)) - Number(selectedIngredients.includes(a.id)));
  }, [searchTerm, selectedIngredients]);

  const toggleIngredient = (id) => {
    setSelectedIngredients((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    setSearchTerm('');
  };

  const canAddCustom =
    searchTerm.trim() &&
    !INGREDIENTS.some((i) => removeEmojis(i.name).toLowerCase() === searchTerm.trim().toLowerCase()) &&
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
      ...INGREDIENTS.filter((i) => selectedIngredients.includes(i.id)).map((i) => removeEmojis(i.name)),
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

  return (
    <div
      className={`search-menu ${
        visible ? 'w-full md:w-1/3' : 'w-0'
      } h-screen md:h-auto overflow-y-auto border-r-2 border-gray-600 shadow-xl shadow-gray-600 flex flex-col p-5 bg-white transition-all duration-300 ease-in-out fixed md:static top-0 left-0 z-40 ${
        visible ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <button className="md:hidden absolute top-4 right-4 text-gray-600" onClick={onClose} aria-label="Close menu">
        <X size={24} />
      </button>

      <h2 className="text-4xl p-1 pl-10 font-bold mb-3 text-gray-800">What&apos;s for Dinner ?</h2>

      <div className="flex items-center md:p-3 pb-3">
        <p className="text-base font-semibold mx-2 mb-2 px-3 py-1 rounded-full bg-green-300 text-green-700">Veg Mode</p>
        <div className="p-1">
          <VegToggle value={isVeg} onChange={setIsVeg} />
        </div>
      </div>

      <div role="tablist" aria-label="Search mode" className="flex flex-wrap gap-2 md:px-3 pb-5">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            role="tab"
            aria-selected={mode === m.id}
            onClick={() => { setMode(m.id); setHint(''); }}
            className={chip(mode === m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === 'describe' ? (
        <div className="mb-8">
          <label htmlFor="describe-input" className="block text-lg font-semibold text-gray-800 mb-2">
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
            className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-sm text-gray-600 mt-2">
            Veg Mode applies. Cuisine and course filters are only used when searching by ingredients.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-8 md:px-3">
            <ModelPicker models={meta.models} value={model} onChange={changeModel} />
          </div>

          <Section title="Ingredients" open={expanded.ingredients} onToggle={() => toggleSection('ingredients')}>
            <div className="mt-4">
              <div className="relative mb-4">
                <input
                  type="text"
                  placeholder="Search ingredients..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') addCustom(); }}
                  className="w-full p-2 pl-10 pr-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Search className="absolute left-3 top-2.5 text-gray-400" size={20} />
                {canAddCustom && (
                  <button
                    type="button"
                    onClick={addCustom}
                    className="absolute right-2 top-2 px-2 py-1 bg-blue-500 text-white rounded-full text-sm"
                  >
                    Add
                  </button>
                )}
              </div>
              <div className="flex p-5 max-h-80 overflow-auto flex-wrap gap-2">
                {displayedIngredients.map((ingredient) => {
                  const on = selectedIngredients.includes(ingredient.id);
                  return (
                    <button
                      key={ingredient.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleIngredient(ingredient.id)}
                      className={chip(on)}
                    >
                      {ingredient.name}
                      {on && <X size={14} className="inline-block ml-1" />}
                    </button>
                  );
                })}
              </div>
              {customIngredients.length > 0 && (
                <div className="mt-4 px-5">
                  <h3 className="font-semibold mb-2 text-gray-700">Custom Ingredients:</h3>
                  <div className="flex flex-wrap gap-2">
                    {customIngredients.map((ingredient) => (
                      <button
                        key={ingredient}
                        type="button"
                        onClick={() => setCustomIngredients(customIngredients.filter((c) => c !== ingredient))}
                        className="px-3 py-1 border-2 border-blue-500 rounded-full text-sm font-medium bg-blue-100 text-blue-700 hover:bg-blue-200 transition duration-200 flex items-center"
                      >
                        {ingredient}
                        <X size={14} className="ml-1" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Section>

          <Section title="Cuisines" open={expanded.cuisines} onToggle={() => toggleSection('cuisines')}>
            <div className="flex p-3 overflow-auto flex-wrap gap-2">
              {meta.cuisines.map((c) => {
                const on = selectedCuisines.includes(c.name);
                return (
                  <button key={c.name} type="button" aria-pressed={on} onClick={() => toggleCuisine(c.name)} className={chip(on)}>
                    {c.name}
                    {on && <X size={14} className="inline-block ml-1" />}
                  </button>
                );
              })}
            </div>
          </Section>

          <Section title="Courses" open={expanded.courses} onToggle={() => toggleSection('courses')}>
            <div className="mt-4 p-5 grid grid-cols-2 md:grid-cols-3 gap-2">
              {meta.courses.map((c) => (
                <label key={c.name} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="course"
                    checked={selectedCourse === c.name}
                    onChange={() => setSelectedCourse(c.name)}
                    className="form-radio h-5 w-5 text-blue-500 focus:ring-blue-400 "
                  />
                  <span className="text-gray-700">{c.name}</span>
                </label>
              ))}
            </div>
          </Section>

          {meta.status === 'loading' && <p className="text-sm text-gray-600 mb-4">Loading cuisines and courses...</p>}
          {meta.status === 'fallback' && (
            <p className="text-sm text-gray-600 mb-4">
              Could not load the full lists from the server. Showing a short default list.
            </p>
          )}

          {likedCount > 0 && (
            <div className="mb-5 flex items-center justify-between gap-2 bg-gray-100 border-2 border-zinc-900 rounded-lg p-3">
              <p className="text-sm text-gray-900">
                Tuned to your likes ({likedCount} liked)
              </p>
              <button type="button" onClick={onClearLikes} className="text-sm font-semibold underline text-gray-700 hover:text-gray-900">
                Clear likes
              </button>
            </div>
          )}
        </>
      )}

      {hint && <p className="text-sm text-red-700 mb-3" role="alert">{hint}</p>}

      <div className="flex justify-between">
        <button
          type="button"
          disabled={busy}
          className="w-1/2 bg-gray-800 text-white py-3 px-4 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 disabled:opacity-60"
          onClick={() => run()}
        >
          Find Recipes
        </button>
        <button
          type="button"
          className="w-1/3 bg-red-300 text-red-800 py-3 px-4 rounded-full text-lg font-semibold hover:bg-red-500 transition duration-200 border
          border-red-800 focus:ring-red-400"
          onClick={clearAll}
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
};

export default SearchPanel;
