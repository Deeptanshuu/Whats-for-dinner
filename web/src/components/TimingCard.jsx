/* eslint-disable react/prop-types */
// The ledger line: how many results, which model, and the server-measured time.
// The current time carries the one hue; the previous run, when it used another model, sits under it in grey.
const fmt = (ms) => `${ms < 10 ? ms.toFixed(2) : ms.toFixed(1)} ms`;

const TimingCard = ({ count, current, previous }) => (
  <div className="text-[15px] leading-relaxed">
    <p className="text-ink">
      <span className="tabular-nums">{count}</span> {count === 1 ? 'result' : 'results'}
      {current && (
        <>
          {' '}from {current.label} in{' '}
          <span className="font-medium tabular-nums text-accent">{fmt(current.ms)}</span>
        </>
      )}
    </p>
    {current && previous && previous.label !== current.label && (
      <p className="text-slate-600">
        Previous run: {previous.label} in <span className="tabular-nums">{fmt(previous.ms)}</span>
      </p>
    )}
  </div>
);

export default TimingCard;
