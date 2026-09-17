import { useState, useEffect } from 'react';

export function useSystemStats() {
  const [stats, setStats] = useState();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/internal/stats');
        if (!res.ok) throw new Error('Falha na comunicação com o Middleware.');
        const data = await res.json();
        setStats(data);
      } catch (error) {
        console.error('Falha na comunicação com o Middleware:', error);
        setStats(prev => ({ ...prev, isConnected: false }));
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    
    const interval = setInterval(fetchStats, 2000); 
    
    return () => clearInterval(interval);
  }, []);

  return { stats, isLoading };
}