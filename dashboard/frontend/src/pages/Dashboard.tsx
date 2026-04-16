import React, { useState, useMemo, useEffect } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { MarketType } from '../types'
import SummaryCards from '../components/SummaryCards'
import JangoTable from '../components/JangoTable'
import ChegeolTable from '../components/ChegeolTable'
import TradeTable from '../components/TradeTable'
import AlertPanel from '../components/AlertPanel'
import { TrendingUp, BarChart3, LineChart, Globe, Zap, Moon as MoonIcon, Plane, Bitcoin, CandlestickChart, Sun, Menu } from 'lucide-react'

const MARKETS: MarketType[] = ['stock', 'stock_etf', 'stock_etn', 'stock_usa', 'future', 'future_nt', 'future_os', 'coin', 'coin_future']
const MARKET_NAMES: Record<MarketType, string> = {
  stock: '국내주식',
  stock_etf: 'ETF',
  stock_etn: 'ETN',
  stock_usa: '미국주식',
  future: '선물',
  future_nt: '선물야간',
  future_os: '해외선물',
  coin: '코인',
  coin_future: '코인선물'
}

export default function Dashboard() {
  const [selectedMarket, setSelectedMarket] = useState<MarketType>(() => {
    const saved = localStorage.getItem('selectedMarket')
    return (saved as MarketType) || 'stock'
  })
  const [isDarkMode, setIsDarkMode] = useState(true)
  const [isMarketDropdownOpen, setIsMarketDropdownOpen] = useState(false)
  const { data, isLoading } = useWebSocket(selectedMarket)

  // selectedMarket이 변경되면 localStorage에 저장
  useEffect(() => {
    localStorage.setItem('selectedMarket', selectedMarket)
  }, [selectedMarket])
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  // 드롭다운 외부 클릭 시 닫기
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsMarketDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 아이콘을 컴포넌트 내부에 정의하여 UMD 전역 변수 참조 에러 해결
  const MARKET_ICONS: Record<MarketType, React.ReactNode> = useMemo(() => ({
    stock: <TrendingUp className="w-4 h-4" />,
    stock_etf: <BarChart3 className="w-4 h-4" />,
    stock_etn: <LineChart className="w-4 h-4" />,
    stock_usa: <Globe className="w-4 h-4" />,
    future: <Zap className="w-4 h-4" />,
    future_nt: <MoonIcon className="w-4 h-4" />,
    future_os: <Plane className="w-4 h-4" />,
    coin: <Bitcoin className="w-4 h-4" />,
    coin_future: <CandlestickChart className="w-4 h-4" />
  }), [])

  // 다크 모드 토글 시 HTML 태그에 dark 클래스 추가/제거
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  // useMemo로 items 데이터 캐싱 - 실제 데이터 변경 시에만 새로운 참조 생성
  const jangoItems = useMemo(() => data?.jangolist ?? [], [data, selectedMarket])
  const chegeolItems = useMemo(() => data?.chegeollist ?? [], [data, selectedMarket])
  const tradeItems = useMemo(() => data?.tradelist ?? [], [data, selectedMarket])

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-100 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4 md:p-6 relative overflow-hidden">
      <div className="max-w-7xl mx-auto space-y-4 md:space-y-6">
        <div className="flex flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">STOM BOARD ＠ {MARKET_NAMES[selectedMarket]}</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsMarketDropdownOpen(!isMarketDropdownOpen)}
                className="p-2 h-10 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 dark:from-gray-700 dark:to-gray-800 hover:from-blue-600 hover:to-purple-600 dark:hover:from-gray-600 dark:hover:to-gray-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
                aria-label="거래소 선택"
              >
                <Menu className="w-5 h-5" />
              </button>
              {isMarketDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                  {MARKETS.map((market) => (
                    <button
                      key={market}
                      onClick={() => {
                        setSelectedMarket(market)
                        setIsMarketDropdownOpen(false)
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${selectedMarket === market ? 'bg-blue-50 dark:bg-blue-900' : ''}`}
                    >
                      {MARKET_ICONS[market]}
                      <span className="text-sm">{MARKET_NAMES[market]}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-2 h-10 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 dark:from-gray-700 dark:to-gray-800 hover:from-blue-600 hover:to-purple-600 dark:hover:from-gray-600 dark:hover:to-gray-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
              aria-label="다크 모드 토글"
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <MoonIcon className="w-5 h-5" />}
            </button>
          </div>
        </div>
        <div className="space-y-3">
          {data && (data.jangolist || data.chegeollist || data.tradelist || data.totaltradelist) ? (
            <>
              {isLoading && (
                <div className="flex items-center justify-center py-2">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">데이터 업데이트 중...</p>
                  </div>
                </div>
              )}
              <SummaryCards totalTrade={data.totaltradelist} market={selectedMarket} timestamp={data.timestamp} />
              <AlertPanel alerts={data.alerts || []} />
              <JangoTable items={jangoItems} />
              <ChegeolTable items={chegeolItems} />
              <TradeTable items={tradeItems} />
            </>
          ) : (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">데이터 로딩 중...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
