/* eslint-disable react/prop-types */
// Controlled: the parent owns the value so Clear can reset it.
const VegToggle = ({ value = false, onChange, id }) => (
  <button
    id={id}
    type="button"
    role="switch"
    aria-checked={value}
    onClick={() => onChange && onChange(!value)}
    className="inline-flex h-11 items-center"
  >
    <span className="sr-only">Vegetarian only</span>
    <span
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 ${
        value ? 'bg-accent' : 'bg-slate-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 rounded-full bg-white transition-transform duration-200 ${
          value ? 'translate-x-[18px]' : 'translate-x-0.5'
        }`}
      />
    </span>
  </button>
);

export default VegToggle;
