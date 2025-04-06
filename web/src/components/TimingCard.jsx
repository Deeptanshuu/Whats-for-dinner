/* eslint-disable react/prop-types */
// Server-measured time for the last search, next to the one before it.
const TimingCard = ({ current, previous }) => {
  const faster = previous && current.ms < previous.ms;
  return (
    <div className="bg-gray-100 border-2 border-zinc-900 rounded-lg p-3 mb-4 col-span-3 flex items-center justify-between">
      <div>
        <p className="text-lg font-semibold text-gray-900">Execution Time</p>
        <p className="text-2xl font-bold text-blue-600">{current.ms.toFixed(2)} ms</p>
        {previous && Math.abs(current.ms - previous.ms) >= 0.005 && (
          <p className={`text-sm ${faster ? 'text-green-600' : 'text-red-600'}`}>
            {faster ? 'Down ' : 'Up '}
            {Math.abs(current.ms - previous.ms).toFixed(2)} ms
            {faster ? ' faster' : ' slower'} than {previous.label} ({previous.ms.toFixed(2)} ms)
          </p>
        )}
      </div>
      <div className="text-right">
        <p className="text-sm text-gray-600">Method: {current.label}</p>
        <p className="text-sm text-gray-600">
          {current.ms < 100 ? 'Lightning fast!' : current.ms < 500 ? 'Pretty quick!' : 'Not too shabby'}
        </p>
      </div>
    </div>
  );
};

export default TimingCard;
