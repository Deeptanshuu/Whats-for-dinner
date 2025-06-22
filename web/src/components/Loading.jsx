/* eslint-disable react/prop-types */
// Quiet loading line: a thin spinning ring and a short label.
const Loading = ({ label = 'Loading' }) => (
  <div className="flex items-center justify-center gap-3 py-16 text-slate-500" role="status" aria-live="polite">
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-ink" aria-hidden="true" />
    <span className="text-[15px]">{label}</span>
  </div>
);

export default Loading;
