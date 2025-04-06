import { useState, useEffect, useRef, useCallback } from 'react';
import { Menu } from 'lucide-react';
import SearchPanel from './SearchPanel';
import ResultsGrid from './ResultsGrid';
import useLikes from '../useLikes';
import { recommend, search, getMeta } from '../api';
import bgImage from './bg.svg';

const PAGE_SIZE = 6;
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

const Home = () => {
  const [meta, setMeta] = useState({ ...FALLBACK_META, status: 'loading' });
  const [results, setResults] = useState({ status: 'idle', items: [], error: '' });
  const [lastRun, setLastRun] = useState(null);
  const [timing, setTiming] = useState({ current: null, previous: null });
  const [page, setPage] = useState(1);
  const [isMenuVisible, setIsMenuVisible] = useState(false);
  const { liked, toggle, clear } = useLikes();
  const resultRef = useRef(null);
  const reqId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    getMeta({ signal: controller.signal })
      .then((data) => {
        const ok = (list) => Array.isArray(list) && list.length > 0;
        setMeta({
          cuisines: ok(data.cuisines) ? data.cuisines : FALLBACK_META.cuisines,
          courses: ok(data.courses) ? data.courses : FALLBACK_META.courses,
          models: ok(data.models) ? data.models : FALLBACK_META.models,
          status: ok(data.cuisines) && ok(data.courses) ? 'ok' : 'fallback',
        });
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setMeta({ ...FALLBACK_META, status: 'fallback' });
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const onResize = () => setIsMenuVisible(window.innerWidth >= 1000);
    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
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
  }, [liked, modelLabel]);

  const clearResults = () => {
    reqId.current += 1;
    setResults({ status: 'idle', items: [], error: '' });
    setLastRun(null);
    setTiming({ current: null, previous: null });
  };

  const paginate = (n) => {
    setPage(n);
    if (resultRef.current) resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div
      className="home flex flex-col md:flex-row bg-white min-h-screen"
      style={{ background: `url(${bgImage}) repeat`, backgroundSize: '500px 500px' }}
    >
      <button
        type="button"
        aria-label="Toggle menu"
        className="fixed top-[1.4rem] left-[1.2rem] z-50 bg-gray-800 text-white p-2 rounded-full shadow-lg"
        onClick={() => setIsMenuVisible((v) => !v)}
      >
        <Menu size={24} />
      </button>

      <SearchPanel
        visible={isMenuVisible}
        onClose={() => setIsMenuVisible(false)}
        meta={meta}
        busy={results.status === 'loading'}
        hasResults={results.status === 'done'}
        likedCount={liked.length}
        onClearLikes={clear}
        onSearch={runSearch}
        onClear={clearResults}
      />

      <div
        ref={resultRef}
        className={`result mb-10 ${isMenuVisible ? 'md:w-2/3' : 'w-full'} transition-all duration-300 ease-in-out p-5`}
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
        />
      </div>
    </div>
  );
};

export default Home;
