import { useState, useMemo, useEffect } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { MarketType } from '../types'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import SummaryCards from '../components/SummaryCards'
import JangoTable from '../components/JangoTable'
import ChegeolTable from '../components/ChegeolTable'
import TradeTable from '../components/TradeTable'
import ProfitChart from '../components/ProfitChart'
import AlertPanel from '../components/AlertPanel'
import { TrendingUp, BarChart3, LineChart, Globe, Zap, Moon as MoonIcon, Plane, Bitcoin, CandlestickChart, Sun } from 'lucide-react'

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

// 아이콘을 컴포넌트 외부에 상수로 정의하여 리렌더링 방지
const MARKET_ICONS: Record<MarketType, React.ReactNode> = {
  stock: <TrendingUp className="w-4 h-4" />,
  stock_etf: <BarChart3 className="w-4 h-4" />,
  stock_etn: <LineChart className="w-4 h-4" />,
  stock_usa: <Globe className="w-4 h-4" />,
  future: <Zap className="w-4 h-4" />,
  future_nt: <MoonIcon className="w-4 h-4" />,
  future_os: <Plane className="w-4 h-4" />,
  coin: <Bitcoin className="w-4 h-4" />,
  coin_future: <CandlestickChart className="w-4 h-4" />
}

export default function Dashboard() {
  const [selectedMarket, setSelectedMarket] = useState<MarketType>('stock')
  const [isDarkMode, setIsDarkMode] = useState(true)
  const { data, connected } = useWebSocket(selectedMarket)

  // 다크 모드 토글 시 HTML 태그에 dark 클래스 추가/제거
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  // useMemo로 items 데이터 캐싱 - 실제 데이터 변경 시에만 새로운 참조 생성
  const jangoItems = useMemo(() => data?.jangolist ?? [], [data?.jangolist])
  const chegeolItems = useMemo(() => data?.chegeollist ?? [], [data?.chegeollist])
  const tradeItems = useMemo(() => data?.tradelist ?? [], [data?.tradelist])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-gray-950 dark:via-slate-900 dark:to-gray-950 p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4 md:space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h1 className="text-2xl md:text-3xl font-bold">STOM 트레이딩 대시보드</h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-2 h-10 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 dark:from-blue-600 dark:to-purple-600 hover:from-blue-600 hover:to-purple-600 dark:hover:from-blue-700 dark:hover:to-purple-700 text-white shadow-md hover:shadow-lg transition-all duration-200"
              aria-label="다크 모드 토글"
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <MoonIcon className="w-5 h-5" />}
            </button>
            <div className="text-sm text-gray-500 h-10 flex items-center">
              {connected ? '● 연결됨' : '○ 연결 안됨'}
            </div>
          </div>
        </div>
        <Tabs value={selectedMarket} onValueChange={(v) => setSelectedMarket(v as MarketType)}>
          <TabsList className="grid w-full grid-cols-3 gap-2 h-auto">
            {MARKETS.map((market) => (
              <TabsTrigger
                key={market}
                value={market}
                className="flex flex-col items-center gap-1 py-3 px-2 text-xs"
              >
                {MARKET_ICONS[market]}
                <span>{MARKET_NAMES[market]}</span>
              </TabsTrigger>
            ))}
          </TabsList>
          
          {MARKETS.map((market) => (
            <TabsContent key={market} value={market} className="space-y-4 md:space-y-6">
              {!connected && (
                <div className="bg-yellow-100 text-yellow-800 p-3 md:p-4 rounded text-sm">
                  연결 중...
                </div>
              )}
              
              {data && (
                <>
                  <SummaryCards totalTrade={data.totaltradelist} />
                  <AlertPanel alerts={data.alerts || []} />
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
                    <JangoTable items={jangoItems} />
                    <ChegeolTable items={chegeolItems} />
                  </div>
                  <ProfitChart trades={tradeItems} />
                  <TradeTable items={tradeItems} />
                </>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  )
}
