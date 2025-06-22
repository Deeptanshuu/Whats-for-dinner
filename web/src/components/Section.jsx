/* eslint-disable react/prop-types */
import { ChevronDown } from 'lucide-react';

// A titled group in the search panel, separated by a hairline, that can fold away.
const Section = ({ title, note, open, onToggle, children }) => (
  <div className="border-t border-slate-200 py-5">
    <button
      type="button"
      aria-expanded={open}
      className="flex min-h-11 w-full items-center justify-between gap-3 text-left lg:min-h-9"
      onClick={onToggle}
    >
      <span className="label">
        {title}
        {note && <span className="ml-2 font-normal text-slate-500">{note}</span>}
      </span>
      <ChevronDown size={18} className={`shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
    </button>
    {open && <div className="mt-3">{children}</div>}
  </div>
);

export default Section;
