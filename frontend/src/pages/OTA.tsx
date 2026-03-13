import { useRobots } from '../hooks/useRobots'
import { OTAManager } from '../components/OTAManager/OTAManager'

export function OTA() {
  const { data: robots = [] } = useRobots()
  return <OTAManager robots={robots} />
}
