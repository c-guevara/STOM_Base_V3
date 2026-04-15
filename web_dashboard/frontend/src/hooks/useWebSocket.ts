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
  const lastDataRef = useRef<DashboardData | null>(null)  // 마지막 데이터 캐싱

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

        // 데이터 변경 감지: 실제 데이터가 변경되었을 때만 업데이트
        const lastData = lastDataRef.current
        if (lastData) {
          const jangoChanged = JSON.stringify(lastData.jangolist) !== JSON.stringify(message.jangolist)
          const chegeolChanged = JSON.stringify(lastData.chegeollist) !== JSON.stringify(message.chegeollist)
          const tradeChanged = JSON.stringify(lastData.tradelist) !== JSON.stringify(message.tradelist)
          const totalTradeChanged = JSON.stringify(lastData.totaltradelist) !== JSON.stringify(message.totaltradelist)

          if (!jangoChanged && !chegeolChanged && !tradeChanged && !totalTradeChanged) {
            return  // 데이터가 변경되지 않으면 업데이트 스킵
          }
        }

        setData(message)
        lastDataRef.current = message
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
    const previousMarket = currentMarketRef.current
    currentMarketRef.current = market
    reconnectAttemptsRef.current = 0
    setData(null)  // 마켓 변경 시 데이터 리셋
    lastDataRef.current = null

    // 거래소가 변경된 경우 기존 연결 강제 종료
    if (previousMarket !== market && wsRef.current) {
      console.log(`[WebSocket] Market changed from ${previousMarket} to ${market}, disconnecting old connection`)
      disconnect(true)
      connectingRef.current = false
    }
  }, [market, disconnect])

  useEffect(() => {
    // market이 변경된 경우 무조건 새로운 연결 시도
    if (wsRef.current?.readyState === WebSocket.OPEN && currentMarketRef.current === market) {
      console.log(`[WebSocket] Already connected to ${market}, skipping`)
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
