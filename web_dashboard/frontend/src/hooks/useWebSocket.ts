import { useState, useEffect, useRef, useCallback } from 'react'
import { DashboardData, MarketType } from '../types'

const WS_URL = `ws://${window.location.hostname}:8000`
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5

export function useWebSocket(market: MarketType) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMountedRef = useRef(true)
  const isIntentionalCloseRef = useRef(false)
  const currentMarketRef = useRef(market)
  const connectingRef = useRef(false)  // 연결 진행 중 플래그

  const connect = useCallback(() => {
    if (!isMountedRef.current || connectingRef.current) return

    // 이미 연결 중이면 스킵
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log(`[WebSocket] Skip connect, already connected/connecting`)
      return
    }

    connectingRef.current = true

    // currentMarketRef에서 최신 마켓값 읽기 (클로저 문제 해결)
    const currentMarket = currentMarketRef.current
    const wsUrl = `${WS_URL}/ws/${currentMarket}`
    console.log(`[WebSocket] Connecting to: ${wsUrl}`)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      if (!isMountedRef.current) return
      console.log(`[WebSocket] Connected to ${currentMarket}`)
      setConnected(true)
      reconnectAttemptsRef.current = 0
      connectingRef.current = false
    }

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return
      try {
        const message = JSON.parse(event.data) as DashboardData
        setData(message)
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error(`[WebSocket] Error on ${currentMarket}:`, error)
    }

    ws.onclose = (event) => {
      if (!isMountedRef.current) return
      console.log(`[WebSocket] ${currentMarket} closed (code: ${event.code}, intentional: ${isIntentionalCloseRef.current})`)
      setConnected(false)
      wsRef.current = null
      connectingRef.current = false

      // 의도적인 종료(탭 변경)시 재연결하지 않음
      if (isIntentionalCloseRef.current) {
        console.log(`[WebSocket] Intentional close, skipping reconnect for ${currentMarket}`)
        return
      }

      // 자동 재연결 - 최신 마켓값으로 재연결
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++
        const latestMarket = currentMarketRef.current
        console.log(`[WebSocket] Reconnecting to ${latestMarket} in ${RECONNECT_DELAY}ms (attempt ${reconnectAttemptsRef.current})`)
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, RECONNECT_DELAY)
      }
    }
  }, [])

  const disconnect = useCallback((intentional = false) => {
    if (intentional) {
      isIntentionalCloseRef.current = true
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // 현재 마켓 추적
  useEffect(() => {
    currentMarketRef.current = market
    reconnectAttemptsRef.current = 0
  }, [market])

  useEffect(() => {
    // Strict Mode 대응: 이미 연결 중이거나 연결 진행 중이면 스킵
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log(`[WebSocket] Already connected/connecting to ${market}, skipping`)
      return
    }

    isMountedRef.current = true
    isIntentionalCloseRef.current = false

    // Strict Mode 대응: setTimeout으로 cleanup 완료 후 연결
    const timeout = setTimeout(() => {
      if (isMountedRef.current && !connectingRef.current) {
        connect()
      }
    }, 0)

    return () => {
      isMountedRef.current = false
      clearTimeout(timeout)
      disconnect(true)  // 의도적인 종료
    }
  }, [market, connect, disconnect])  // market 변경 시 재연결

  return { data, connected }
}
