import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function StatusComponent() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setLoading(true);
        const data = await api.getHealth();
        setStatus(data.status);
      } catch (err) {
        setError('Failed to connect to API');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  return (
    <div className="mb-6 p-4 border border-border rounded-md">
      <h2 className="text-lg font-medium mb-2 text-foreground">API Status</h2>
      {loading ? (
        <p className="text-muted-foreground">Checking connection...</p>
      ) : error ? (
        <p className="text-destructive">{error}</p>
      ) : (
        <p className="text-green-600 dark:text-green-400">Backend API is {status}</p>
      )}
    </div>
  );
}