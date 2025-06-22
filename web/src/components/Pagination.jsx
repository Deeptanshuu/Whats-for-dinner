/* eslint-disable react/prop-types */
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({ total, pageSize, currentPage, onPage }) => {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return null;
  const numbers = Array.from({ length: pages }, (_, i) => i + 1);
  const arrow = 'inline-flex h-11 w-11 items-center justify-center rounded-full text-slate-600 transition-colors hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent';

  const first = (currentPage - 1) * pageSize + 1;
  const last = Math.min(currentPage * pageSize, total);
  return (
    <nav aria-label="Result pages" className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between">
      <p className="text-sm tabular-nums text-slate-600">{first}-{last} of {total}</p>
      <div className="flex items-center gap-1">
      <button onClick={() => onPage(currentPage - 1)} disabled={currentPage === 1} aria-label="Previous page" className={arrow}>
        <ChevronLeft size={20} />
      </button>
      {numbers.map((number) => (
        <button
          key={number}
          onClick={() => onPage(number)}
          aria-current={currentPage === number ? 'page' : undefined}
          className={`inline-flex h-11 w-11 items-center justify-center rounded-full text-[15px] transition-colors ${
            currentPage === number ? 'bg-[#ebe9e4] font-medium text-ink' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          {number}
        </button>
      ))}
      <button onClick={() => onPage(currentPage + 1)} disabled={currentPage === pages} aria-label="Next page" className={arrow}>
        <ChevronRight size={20} />
      </button>
      </div>
    </nav>
  );
};

export default Pagination;
