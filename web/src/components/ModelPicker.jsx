/* eslint-disable react/prop-types */
// Pick which model ranks the results.
const ModelPicker = ({ models, value, onChange }) => (
  <div>
    <p className="label mb-3" id="model-label">Model</p>
    <div role="radiogroup" aria-labelledby="model-label" className="flex flex-wrap gap-2">
      {models.map((m) => (
        <button
          key={m.id}
          type="button"
          role="radio"
          aria-checked={value === m.id}
          onClick={() => onChange(m.id)}
          className={`chip ${value === m.id ? 'chip-on' : ''}`}
        >
          {m.label}
        </button>
      ))}
    </div>
  </div>
);

export default ModelPicker;
