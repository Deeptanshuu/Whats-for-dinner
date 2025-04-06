/* eslint-disable react/prop-types */
import { ChevronDown, ChevronUp } from 'lucide-react';

const Section = ({ title, open, onToggle, children }) => (
  <div className="mb-8">
    <button
      type="button"
      className="flex items-center justify-between w-full p-3 bg-gray-300 rounded-lg text-lg font-semibold text-white-700 hover:bg-gray-200 transition duration-200"
      onClick={onToggle}
    >
      <span>{title}</span>
      {open ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
    </button>
    {open && children}
  </div>
);

export default Section;
