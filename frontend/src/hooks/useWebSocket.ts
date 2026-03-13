import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Robot, WsMessage } from '../types/robot'

export function useWebSocket() {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Store connect in a ref so onclose can schedule reconnect without circular deps
  const connectRef = useRef<() => void>(() => {})

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === 'initial_state') {
      qc.setQueryData(['robots'], msg.robots)
    } else if (msg.type === 'robot_update') {
      qc.setQueryData<Robot[]>(['robots'], (prev) => {
        if (!prev) return [msg.robot]
        const idx = prev.findIndex((r) => r.robot_id === msg.robot.robot_id)
        if (idx === -1) return [...prev, msg.robot]
        const next = [...prev]
        next[idx] = msg.robot
        return next
      })
      qc.setQueryData(['robots', msg.robot.robot_id], msg.robot)
    }
  }, [qc])

  const connect = useCallback(() => {
    // ローカル: ws://localhost:8000/ws
    // 本番: VITE_WS_URL (wss://xxx.execute-api.xxx.amazonaws.com/dev)
    const url = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}/ws`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[WS] connected')
      ws.send(JSON.stringify({ action: 'subscribe_robot' }))
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage
        handleMessage(msg)
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      console.log('[WS] disconnected, reconnecting in 3s...')
      reconnectTimer.current = setTimeout(() => connectRef.current(), 3000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [handleMessage])

  // Keep ref in sync with latest connect callback
  useLayoutEffect(() => { connectRef.current = connect }, [connect])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])
}
