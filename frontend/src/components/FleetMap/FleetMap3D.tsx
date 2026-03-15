import { OrbitControls, Text } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import { memo, useRef } from 'react';
import { type Mesh, Vector3 } from 'three';
import type { Robot, RobotStatus } from '../../types/robot';

// ─── 定数 ─────────────────────────────────────────────────
const ROOMS = [
  { id: 'living_room', label: 'リビング', x: 1, z: 0, w: 5, d: 4, color: '#e2e8f0' },
  { id: 'kitchen', label: 'キッチン', x: 6, z: 0, w: 4, d: 4, color: '#fef9c3' },
  { id: 'bedroom_1', label: '寝室1', x: 0, z: 4, w: 5, d: 4, color: '#ede9fe' },
  { id: 'bedroom_2', label: '寝室2', x: 5, z: 4, w: 5, d: 4, color: '#fce7f3' },
  { id: 'charging_dock', label: '充電ドック', x: 0, z: 0, w: 1, d: 1, color: '#dcfce7' },
];

const STATUS_COLOR: Record<RobotStatus, string> = {
  IDLE: '#94a3b8',
  CLEANING: '#3b82f6',
  CHARGING: '#22c55e',
  RETURNING_TO_DOCK: '#f59e0b',
  LOW_BATTERY: '#f97316',
  UPDATING: '#a855f7',
  ERROR: '#ef4444',
};

const STATUS_LABELS: Record<RobotStatus, string> = {
  IDLE: '待機中',
  CLEANING: '掃除中',
  CHARGING: '充電中',
  RETURNING_TO_DOCK: 'ドックへ',
  LOW_BATTERY: '低バッテリー',
  UPDATING: 'OTA更新中',
  ERROR: 'エラー',
};

// ─── 部屋 (静的 → memo でスキップ) ──────────────────────
const Wall = memo(function Wall({
  pos,
  w,
  rotY = 0,
}: {
  pos: [number, number, number];
  w: number;
  rotY?: number;
}) {
  return (
    <mesh position={pos} rotation={[0, rotY, 0]}>
      <boxGeometry args={[w, 0.5, 0.06]} />
      {/* Lambert: 壁に PBR 不要 */}
      <meshLambertMaterial color="#cbd5e1" />
    </mesh>
  );
});

const Room = memo(function Room({ room }: { room: (typeof ROOMS)[0] }) {
  const cx = room.x + room.w / 2;
  const cz = room.z + room.d / 2;
  return (
    <group position={[cx, 0, cz]}>
      <mesh receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[room.w - 0.05, 0.05, room.d - 0.05]} />
        <meshLambertMaterial color={room.color} />
      </mesh>
      <Wall pos={[0, 0, -room.d / 2 + 0.03]} w={room.w} />
      <Wall pos={[0, 0, room.d / 2 - 0.03]} w={room.w} />
      <Wall pos={[-room.w / 2 + 0.03, 0, 0]} w={room.d} rotY={Math.PI / 2} />
      <Wall pos={[room.w / 2 - 0.03, 0, 0]} w={room.d} rotY={Math.PI / 2} />
      <Text
        position={[0, 0.5, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={room.id === 'charging_dock' ? 0.25 : 0.4}
        color="#475569"
        anchorX="center"
        anchorY="middle"
      >
        {room.label}
      </Text>
    </group>
  );
});

const ChargingDock = memo(function ChargingDock() {
  return (
    <group position={[0.5, 0.05, 0.5]}>
      <mesh>
        <cylinderGeometry args={[0.35, 0.35, 0.04, 16]} />
        <meshStandardMaterial color="#16a34a" emissive="#16a34a" emissiveIntensity={0.5} />
      </mesh>
      <mesh position={[0, 0.03, 0]}>
        <torusGeometry args={[0.3, 0.03, 6, 16]} />
        <meshStandardMaterial color="#4ade80" emissive="#4ade80" emissiveIntensity={2} />
      </mesh>
    </group>
  );
});

// ─── ロボット ──────────────────────────────────────────────
const LERP_SPEED = 12;

function RobotMesh({ robot, onSelect }: { robot: Robot; onSelect?: (id: string) => void }) {
  const groupRef = useRef<import('three').Group>(null);
  const bodyRef = useRef<Mesh>(null);
  const brushRef = useRef<Mesh>(null);
  const glowRef = useRef<Mesh>(null);

  const visualPos = useRef(new Vector3(robot.position.x, 0.1, robot.position.y));
  const heading = useRef(0);

  const color = STATUS_COLOR[robot.status] ?? '#94a3b8';
  const isCleaning = robot.status === 'CLEANING';
  const isMoving = robot.status === 'CLEANING' || robot.status === 'RETURNING_TO_DOCK';
  const isError = robot.status === 'ERROR';

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    const nowSec = performance.now() / 1000;
    const targetX = robot.position.x;
    const targetZ = robot.position.y;

    // ─ 位置 lerp (LERP_SPEED=12 なら 0.3s 以内に 97% 追従できるためデッドレコニング不要) ─
    const t = Math.min(LERP_SPEED * delta, 1);
    visualPos.current.x += (targetX - visualPos.current.x) * t;
    visualPos.current.z += (targetZ - visualPos.current.z) * t;
    groupRef.current.position.set(visualPos.current.x, 0.1, visualPos.current.z);

    // ─ 向き: 視覚位置→目標の差分方向へスムーズに回転 ─
    if (isMoving) {
      const dx = targetX - visualPos.current.x;
      const dz = targetZ - visualPos.current.z;
      if (Math.abs(dx) + Math.abs(dz) > 0.02) {
        const targetAngle = Math.atan2(dx, dz);
        let diff = targetAngle - heading.current;
        while (diff > Math.PI) diff -= 2 * Math.PI;
        while (diff < -Math.PI) diff += 2 * Math.PI;
        heading.current += diff * Math.min(8 * delta, 1);
        groupRef.current.rotation.y = heading.current;
      }
    }

    // ─ ブラシ回転 ─
    if (brushRef.current && isCleaning) {
      brushRef.current.rotation.y += delta * 5;
    }

    // ─ 上下バウンス ─
    if (bodyRef.current && isMoving) {
      bodyRef.current.position.y = Math.sin(nowSec * 8) * 0.01;
    }

    // ─ グロー点滅 ─
    if (glowRef.current) {
      glowRef.current.scale.setScalar(1 + Math.sin(nowSec * 3) * 0.15);
      // biome-ignore lint/suspicious/noExplicitAny: Three.js material
      (glowRef.current.material as any).opacity = isError
        ? 0.4 + Math.sin(nowSec * 6) * 0.3
        : isCleaning
          ? 0.15 + Math.sin(nowSec * 2) * 0.1
          : 0;
    }
  });

  return (
    // Three.js <group> is not a DOM element; onClick is handled by R3F raycasting
    // biome-ignore lint/a11y/noStaticElementInteractions: 3D canvas element
    <group
      ref={groupRef}
      position={[visualPos.current.x, 0.1, visualPos.current.z]}
      onClick={() => onSelect?.(robot.robot_id)}
    >
      {/* グロー */}
      <mesh ref={glowRef}>
        <cylinderGeometry args={[0.42, 0.42, 0.05, 16]} />
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0}
          emissive={color}
          emissiveIntensity={2}
        />
      </mesh>

      {/* ボディ */}
      <mesh ref={bodyRef} castShadow>
        <cylinderGeometry args={[0.3, 0.32, 0.1, 16]} />
        <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
      </mesh>

      {/* ドーム */}
      <mesh position={[0, 0.08, 0]} castShadow>
        <sphereGeometry args={[0.3, 16, 8, 0, Math.PI * 2, 0, Math.PI / 3]} />
        <meshStandardMaterial color={color} metalness={0.5} roughness={0.3} />
      </mesh>

      {/* 充電中: センサーリング */}
      {robot.status === 'CHARGING' && (
        <mesh position={[0, 0.14, 0]}>
          <torusGeometry args={[0.25, 0.015, 6, 16]} />
          <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={2} />
        </mesh>
      )}

      {/* 掃除中: ブラシ */}
      {isCleaning && (
        <mesh ref={brushRef} position={[0, -0.03, 0]}>
          <torusGeometry args={[0.2, 0.02, 6, 16]} />
          <meshStandardMaterial color="#93c5fd" emissive="#3b82f6" emissiveIntensity={1} />
        </mesh>
      )}

      {/* バッテリー低下: 警告リング */}
      {robot.battery_level < 20 && (
        <mesh position={[0, 0.16, 0]}>
          <torusGeometry args={[0.28, 0.02, 6, 16]} />
          <meshStandardMaterial color="#f97316" emissive="#f97316" emissiveIntensity={3} />
        </mesh>
      )}

      <Text
        position={[0, 0.55, 0]}
        rotation={[-Math.PI / 4, 0, 0]}
        fontSize={0.22}
        color="white"
        anchorX="center"
        anchorY="bottom"
        outlineWidth={0.03}
        outlineColor="#1e293b"
      >
        {robot.robot_id.replace('robot-', 'R')}
      </Text>
    </group>
  );
}

// ─── メインコンポーネント ─────────────────────────────────
interface Props {
  robots: Robot[];
  onSelect?: (robotId: string) => void;
}

export function FleetMap({ robots, onSelect }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-900 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
          フロアマップ 3D
        </h2>
        <span className="text-xs text-slate-500">ドラッグで回転・スクロールでズーム</span>
      </div>

      <div style={{ height: 420 }}>
        <Canvas
          shadows
          camera={{ position: [5, 8, 12], fov: 45 }}
          // dpr を 1.5 上限に抑えて高 DPI 端末の負荷を下げる
          dpr={[1, 1.5]}
          gl={{ antialias: true, powerPreference: 'high-performance' }}
        >
          <color attach="background" args={['#0f172a']} />
          <fog attach="fog" args={['#0f172a', 20, 40]} />

          <ambientLight intensity={0.4} />
          {/* shadow-mapSize を 512 に削減 (2048→512 で GPU 負荷 1/16) */}
          <directionalLight
            position={[10, 15, 10]}
            intensity={1.2}
            castShadow
            shadow-mapSize={[512, 512]}
          />
          <pointLight position={[5, 3, 4]} intensity={0.5} color="#818cf8" />
          {/* Environment (HDR) を除去 → 代わりに hemisphereLight で環境光を補完 */}
          <hemisphereLight args={['#818cf8', '#1e293b', 0.3]} />

          {/* フロア */}
          <mesh receiveShadow position={[5, -0.03, 4]}>
            <boxGeometry args={[10.1, 0.06, 8.1]} />
            <meshLambertMaterial color="#1e293b" />
          </mesh>

          {ROOMS.map((room) => (
            <Room key={room.id} room={room} />
          ))}

          <ChargingDock />

          {robots.map((robot) => (
            <RobotMesh key={robot.robot_id} robot={robot} onSelect={onSelect} />
          ))}

          <OrbitControls
            target={[5, 0, 4]}
            minDistance={3}
            maxDistance={20}
            maxPolarAngle={Math.PI / 2.2}
          />
        </Canvas>
      </div>

      <div className="flex flex-wrap gap-3 px-4 py-2 border-t border-slate-700">
        {Object.entries(STATUS_COLOR).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1 text-xs text-slate-400">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {STATUS_LABELS[status as RobotStatus]}
          </div>
        ))}
      </div>
    </div>
  );
}
