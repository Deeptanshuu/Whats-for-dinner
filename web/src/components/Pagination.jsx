/* eslint-disable react/prop-types */
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({ total, pageSize, currentPage, onPage }) => {
  const pages = Math.ceil(total / pageSize);
  const numbers = Array.from({ length: pages }, (_, i) => i + 1);

  return (
    <div className="flex justify-center items-center space-x-2 mt-4">
      <button
        onClick={() => onPage(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="Previous page"
        className="p-2 rounded-full bg-gray-200 disabled:opacity-50"
      >
        <ChevronLeft size={20} />
      </button>
      {numbers.map((number) => (
        <button
          key={number}
          onClick={() => onPage(number)}
          className={`px-3 py-1 rounded-full ${
            currentPage === number ? 'bg-gray-800 text-white' : 'bg-gray-200'
          }`}
        >
          {number}
        </button>
      ))}
      <button
        onClick={() => onPage(currentPage + 1)}
        disabled={currentPage === pages}
        aria-label="Next page"
        className="p-2 rounded-full bg-gray-200 disabled:opacity-50"
      >
        <ChevronRight size={20} />
      </button>
    </div>
  );
};

export default Pagination;
