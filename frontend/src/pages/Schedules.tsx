import { ScheduleManager } from '../components/ScheduleManager/ScheduleManager';
import { useRobots } from '../hooks/useRobots';

export function Schedules() {
  const { data: robots = [] } = useRobots();
  return <ScheduleManager robots={robots} />;
}
