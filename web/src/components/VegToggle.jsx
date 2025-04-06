/* eslint-disable react/prop-types */
// Controlled: the parent owns the value so Clear can reset it.
const VegToggle = ({ value = false, onChange }) => {
  return (
    <button
      type="button"
      aria-pressed={value}
      onClick={() => onChange && onChange(!value)}
      className={`relative inline-flex items-center ring-2 ring-offset-2   h-6 rounded-full w-11 focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ease-in-out duration-200 ${
        value ? 'bg-green-500 ring-green-500' : 'bg-stone-400 ring-stone-500 focus:ring-green-500'
      }`}
    >
      <span className="sr-only">Toggle vegetarian</span>
      <span
        className={`inline-block w-4 h-4 transform rounded-full bg-white transition ease-in-out duration-200 ${
          value ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
};

export default VegToggle;
