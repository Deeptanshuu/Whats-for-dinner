import { useEffect, useState } from 'react';
import { checkHealth } from '../api';

// Shown only when the health check fails.
const WarningHeader = () => {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    checkHealth({ signal: controller.signal })
      .then(() => setOffline(false))
      .catch((err) => {
        if (err.name !== 'AbortError') setOffline(true);
      });
    return () => controller.abort();
  }, []);

  if (!offline) return null;

  return (
    <div className="border-b border-red-100 bg-red-50 px-4 py-3 text-center text-[15px] text-red-800" role="alert">
      <strong className="font-semibold">Warning:</strong> Server is offline and not reachable. Please check your internet connection or try again later.
    </div>
  );
};

export default WarningHeader;
