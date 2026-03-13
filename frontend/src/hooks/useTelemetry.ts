import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export function useTelemetry(robotId: string, minutes = 60) {
  return useQuery({
    queryKey: ['telemetry', robotId, minutes],
    queryFn: () => api.telemetry.get(robotId, minutes),
    enabled: !!robotId,
    refetchInterval: 10000,
  });
}
