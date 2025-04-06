/* eslint-disable react/prop-types */
import Loading from './Loading';
import RecipeCard from './RecipeCard';
import Pagination from './Pagination';
import TimingCard from './TimingCard';

const Chip = ({ label }) => (
  <div className="flex items-center bg-gray-200 text-gray-800 px-2 py-1 rounded-full mr-2 m-1 min-w-max">
    <span>{label}</span>
  </div>
);

const Notice = ({ children }) => (
  <div className="col-span-3 w-full px-3 p-6 mb-64 md:mb-0 my-64 text-center text-black bg-white border-2 border-black rounded-lg">
    {children}
  </div>
);

const FilterSummary = ({ run }) => {
  const rows = [];
  if (run.mode === 'describe') {
    rows.push(['Search:', [run.query]]);
  } else {
    if (run.ingredients.length) rows.push(['Ingredients:', run.ingredients]);
    if (run.cuisine.length) rows.push(['Cuisines:', run.cuisine]);
    if (run.course) rows.push(['Course:', [run.course]]);
  }
  if (run.veg) rows.push(['Diet:', ['Veg only']]);
  if (!rows.length) return null;
  return (
    <div className="bg-gray-100 border-2 border-zinc-900 rounded-lg p-3 mb-1 m-0 col-span-3">
      <h2 className="text-lg font-semibold text-gray-900">Selected Filters:</h2>
      <div className="flex flex-wrap gap-2 mt-2">
        {rows.map(([label, items]) => (
          <div key={label} className="flex items-center flex-wrap">
            <span className="font-semibold">{label}</span>
            {items.map((it) => <Chip key={it} label={it} />)}
          </div>
        ))}
      </div>
    </div>
  );
};

const ResultsGrid = ({
  status, error, items, run, timing, page, pageSize, onPage, liked, onToggleLike, onRetry,
}) => {
  let body;
  if (status === 'loading') {
    body = (
      <div className="col-span-3 flex flex-row items-center justify-center w-full h-screen pt-64">
        <Loading />
      </div>
    );
  } else if (status === 'error') {
    body = (
      <Notice>
        <h1 className="text-3xl font-bold mb-3">Something went wrong</h1>
        <p className="text-gray-700 mb-4" role="alert">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="bg-gray-800 text-white py-3 px-6 rounded-full text-lg font-semibold hover:bg-gray-700 transition duration-200"
        >
          Try again
        </button>
      </Notice>
    );
  } else if (status === 'idle') {
    body = <Notice><h1 className="text-4xl font-bold">Use the filters to get started</h1></Notice>;
  } else {
    const start = (page - 1) * pageSize;
    body = (
      <>
        <h1 className="text-4xl bg-white font-bold m-2 pl-5 p-4 border-2 rounded-lg  border-slate-800 col-span-3">
          {items.length ? 'Our Top Results' : 'No matches'}
        </h1>
        {run && <FilterSummary run={run} />}
        {timing.current && <TimingCard current={timing.current} previous={timing.previous} />}
        {items.length === 0 && (
          <Notice>
            <h1 className="text-2xl font-bold mb-2">No recipes matched</h1>
            <p className="text-gray-700">Try fewer filters, different ingredients, or switch the model.</p>
          </Notice>
        )}
        {items.slice(start, start + pageSize).map((recipe) => (
          <RecipeCard
            key={recipe.id}
            recipe={recipe}
            newTab
            liked={liked.includes(recipe.id)}
            onToggleLike={() => onToggleLike(recipe.id)}
          />
        ))}
        {items.length > 0 && (
          <div className="col-span-3 bg-white pb-3 p-0 md:ml-96 md:mr-72 m-0 border-2 border-slate-800 rounded-full">
            <Pagination total={items.length} pageSize={pageSize} currentPage={page} onPage={onPage} />
          </div>
        )}
      </>
    );
  }
  return <div className="md:grid md:grid-cols-3 md:gap-7 flex flex-col gap-10">{body}</div>;
};

export default ResultsGrid;
