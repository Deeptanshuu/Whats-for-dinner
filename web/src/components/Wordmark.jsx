/* eslint-disable react/prop-types */
import { Link } from 'react-router-dom';

// Chef's hat line icon and the serif name, as in the README banner.
const Wordmark = ({ className = '' }) => (
  <Link to="/" className={`inline-flex min-h-11 items-center gap-2.5 text-ink ${className}`} aria-label="RecipeSense home">
    <svg
      viewBox="0 0 24 24"
      className="h-7 w-7 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z" />
      <path d="M6 17h12" />
    </svg>
    <span className="font-serif text-[28px] font-semibold leading-none tracking-tight">RecipeSense</span>
  </Link>
);

export default Wordmark;
