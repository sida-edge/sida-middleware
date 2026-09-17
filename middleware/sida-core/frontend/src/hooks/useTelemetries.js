import { useState, useEffect } from 'react';

export function useTelemetries() {
  const [telemetries, setTelemetries] = useState();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/internal/telemetry');
        if (!res.ok) throw new Error('Falha na comunicação com o Middleware.');
        const data = await res.json();
        setTelemetries(prevData => {
            const newData = { ...prevData };
            const currentTime = new Date().toLocaleTimeString();
            if (Array.isArray(data)) {
                data.forEach(item => {
                    if (item.service) {
                        newData[item.service] = {
                            data: item.data,
                            timestamp: item.timestamp || currentTime
                        };
                    }
                });
            } else if (data && data.service) {
                newData[data.service] = {
                    data: data.data,
                    timestamp: data.timestamp || currentTime
                };
            }
            return newData;
        });
      } catch (error) {
        console.error('Falha na comunicação com o Middleware:', error);
        setTelemetries({}); // Reset to empty object on error
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 500); 
    return () => clearInterval(interval);
  }, []);

  return { telemetries, isLoading };
}