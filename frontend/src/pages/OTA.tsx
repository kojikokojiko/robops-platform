import { OTAManager } from '../components/OTAManager/OTAManager';
import { useRobots } from '../hooks/useRobots';

export function OTA() {
  const { data: robots = [] } = useRobots();
  return <OTAManager robots={robots} />;
}
