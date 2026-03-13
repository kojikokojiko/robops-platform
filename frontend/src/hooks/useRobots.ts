import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { RobotCommand } from '../types/robot'

export function useRobots() {
  return useQuery({
    queryKey: ['robots'],
    queryFn: api.robots.list,
    refetchInterval: 5000, // WebSocket が切れても5秒ごとにポーリング
  })
}

export function useRobot(robotId: string) {
  return useQuery({
    queryKey: ['robots', robotId],
    queryFn: () => api.robots.get(robotId),
    enabled: !!robotId,
  })
}

export function useSendCommand(robotId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (cmd: RobotCommand) => api.robots.sendCommand(robotId, cmd),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['robots', robotId] })
    },
  })
}
