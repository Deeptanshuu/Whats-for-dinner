import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import SearchPanel from './SearchPanel';
import ResultsGrid from './ResultsGrid';
import useLikes from '../useLikes';
import { recommend, search, getMeta } from '../api';
import Wordmark from './Wordmark';
import { useStored, getStored, setStored, clearStored } from '../searchStore';

const PAGE_SIZE = 12;
const TAGLINE = 'Type what is in your kitchen. Get recipes that use it.';
const RESULT_LIMIT = 60;

// Used when /api/meta cannot be reached.
const FALLBACK_META = {
  cuisines: ['American', 'Asian', 'French', 'Indian', 'Italian', 'Japanese', 'Mexican', 'Thai'].map((name) => ({ name })),
  courses: ['Appetizer', 'Breakfast', 'Dessert', 'Main Course', 'Salad', 'Side Dish', 'Soup'].map((name) => ({ name })),
  models: [
    { id: 'learned', label: 'Learned ranker' },
    { id: 'embedding', label: 'Ingredient embeddings' },
    { id: 'overlap', label: 'Ingredient overlap' },
    { id: 'tfidf', label: 'TF-IDF' },
  ],
};

// A search that was still running when the page was left cannot be resumed; show what was there before it.
const settled = (r) => (r.status === 'loading' ? { ...r, status: r.items.length ? 'done' : 'idle' } : r);

const Home = () => {
  // Everything about the search lives in the store, so coming back from a recipe
  // shows the screen as it was left without asking the server again.
  const [meta, setMeta] = useState(() => getStored('meta', { ...FALLBACK_META, status: 'loading' }));
  const [results, setResults] = useStored('results', { status: 'idle', items: [], error: '' });
  const [lastRun, setLastRun] = useStored('lastRun', null);
  const [timing, setTiming] = useStored('timing', { current: null, previous: null });
  const [page, setPage] = useStored('page', 1);
  // Phones only: after a search the controls fold into an "Edit search" row so results come first.
  const [collapsed, setCollapsed] = useStored('collapsed', false);
  // An example description picked on the empty screen; the panel fills itself in and runs it.
  const [preset, setPreset] = useState(null);
  const { liked, toggle, clear } = useLikes();
  const resultRef = useRef(null);
  const reqId = useRef(0);

  useLayoutEffect(() => {
    setResults(settled);
  }, [setResults]);

  useEffect(() => {
    const controller = new AbortController();
    getMeta({ signal: controller.signal })
      .then((data) => {
        const ok = (list) => Array.isArray(list) && list.length > 0;
        const next = {
          cuisines: ok(data.cuisines) ? data.cuisines : FALLBACK_META.cuisines,
          courses: ok(data.courses) ? data.courses : FALLBACK_META.courses,
          models: ok(data.models) ? data.models : FALLBACK_META.models,
          status: ok(data.cuisines) && ok(data.courses) ? 'ok' : 'fallback',
        };
        // Keep the lists already on screen when nothing changed, so the panel does not redraw.
        setMeta((prev) => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next));
        if (next.status === 'ok') setStored('meta', next);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setMeta((prev) => (prev.status === 'ok' ? prev : { ...FALLBACK_META, status: 'fallback' }));
      });
    return () => controller.abort();
  }, []);

  const modelLabel = useCallback(
    (id) => (meta.models.find((m) => m.id === id) || { label: id }).label,
    [meta.models]
  );

  const runSearch = useCallback(async (params) => {
    const id = ++reqId.current;
    setLastRun(params);
    setResults((r) => ({ ...r, status: 'loading', error: '' }));
    try {
      let data;
      let label;
      if (params.mode === 'describe') {
        data = await search({ query: params.query, veg: params.veg, limit: RESULT_LIMIT });
        label = 'Free-text search';
      } else {
        data = await recommend({
          ingredients: params.ingredients,
          cuisine: params.cuisine,
          course: params.course,
          veg: params.veg,
          model: params.model,
          liked,
          limit: RESULT_LIMIT,
        });
        label = modelLabel(data.model || params.model);
      }
      if (id !== reqId.current) return;
      setResults({ status: 'done', items: data.recommendations || [], error: '' });
      if (typeof data.execution_time === 'number') {
        setTiming((t) => ({ current: { ms: data.execution_time, label }, previous: t.current }));
      }
      setPage(1);
    } catch (err) {
      if (id !== reqId.current) return;
      setResults({ status: 'error', items: [], error: err.message });
    }
  }, [liked, modelLabel, setLastRun, setResults, setTiming, setPage]);

  const isPhone = () => window.matchMedia('(max-width: 1023px)').matches;

  const startSearch = (params) => {
    if (isPhone()) {
      setCollapsed(true);
      window.scrollTo({ top: 0 });
    }
    runSearch(params);
  };

  const clearResults = () => {
    reqId.current += 1;
    setCollapsed(false);
    setResults({ status: 'idle', items: [], error: '' });
    setLastRun(null);
    setTiming({ current: null, previous: null });
    setPage(1);
    clearStored();
  };

  const paginate = (n) => {
    setPage(n);
    if (resultRef.current) resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="mx-auto min-h-screen max-w-[1440px] lg:flex">
      <aside className="lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-[400px] lg:shrink-0 lg:flex-col lg:border-r lg:border-slate-200">
        <header className="px-5 pb-6 pt-7 lg:px-8 lg:pt-9">
          <Wordmark />
          {/* Below the desktop layout the empty-state heading is hidden, so the tagline is the page title there. */}
          {results.status === 'idle' ? (
            <>
              <h1 className="mt-1 text-balance text-[15px] font-normal text-slate-500 lg:hidden">{TAGLINE}</h1>
              <p className="mt-1 hidden text-balance text-[15px] text-slate-500 lg:block">{TAGLINE}</p>
            </>
          ) : (
            <p className="mt-1 text-balance text-[15px] text-slate-500">{TAGLINE}</p>
          )}
        </header>

        {collapsed && (
          <div className="px-5 lg:hidden">
            <button type="button" onClick={() => setCollapsed(false)} className="btn-quiet w-full gap-2">
              <SlidersHorizontal size={16} aria-hidden="true" />
              Edit search
            </button>
          </div>
        )}

        <SearchPanel
          className={`${collapsed ? 'hidden' : 'flex'} lg:flex lg:min-h-0 lg:flex-1`}
          meta={meta}
          busy={results.status === 'loading'}
          hasResults={results.status === 'done'}
          likedCount={liked.length}
          onClearLikes={clear}
          onSearch={startSearch}
          onClear={clearResults}
          preset={preset}
        />
      </aside>

      <main
        ref={resultRef}
        className={`min-w-0 flex-1 scroll-mt-4 px-5 pb-16 pt-8 lg:px-12 lg:pt-9 ${
          results.status === 'idle' ? 'hidden lg:block' : ''
        } ${collapsed || results.status === 'idle' ? '' : 'border-t border-slate-200 lg:border-t-0'}`}
      >
        <ResultsGrid
          status={results.status}
          error={results.error}
          items={results.items}
          run={lastRun}
          timing={timing}
          page={page}
          pageSize={PAGE_SIZE}
          onPage={paginate}
          liked={liked}
          onToggleLike={toggle}
          onRetry={() => lastRun && runSearch(lastRun)}
          onExample={(query) => setPreset({ query, at: Date.now() })}
        />
      </main>
    </div>
  );
};

export default Home;
