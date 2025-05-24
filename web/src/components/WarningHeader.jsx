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
    <div className="bg-yellow-500 text-white text-center py-3 text-xl">
      <strong>Warning:</strong> Server is offline and not reachable. Please check your internet connection or try again later.
    </div>
  );
};

export default WarningHeader;
