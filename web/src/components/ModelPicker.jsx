/* eslint-disable react/prop-types */
// Pick which model ranks the results.
const ModelPicker = ({ models, value, onChange }) => (
  <div>
    <p className="text-sm font-semibold text-gray-700 mb-2">Recommendation model</p>
    <div role="radiogroup" aria-label="Recommendation model" className="flex flex-wrap gap-2">
      {models.map((m) => (
        <button
          key={m.id}
          type="button"
          role="radio"
          aria-checked={value === m.id}
          onClick={() => onChange(m.id)}
          className={`px-3 py-1 border-2 border-slate-500 rounded-full text-m font-medium transition duration-200 ${
            value === m.id ? 'bg-stone-700 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  </div>
);

export default ModelPicker;
