import { useRobots } from '../hooks/useRobots'
import { ScheduleManager } from '../components/ScheduleManager/ScheduleManager'

export function Schedules() {
  const { data: robots = [] } = useRobots()
  return <ScheduleManager robots={robots} />
}
