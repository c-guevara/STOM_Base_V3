import { useState } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { MarketType } from '../types'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import SummaryCards from '../components/SummaryCards'
import JangoTable from '../components/JangoTable'
import ChegeolTable from '../components/ChegeolTable'
import TradeTable from '../components/TradeTable'
import ProfitChart from '../components/ProfitChart'
import AlertPanel from '../components/AlertPanel'

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
  const [selectedMarket, setSelectedMarket] = useState<MarketType>('stock')
  const { data, connected } = useWebSocket(selectedMarket)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4 md:space-y-6">
        {/* 세련된 헤더 카드 */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-6 shadow-2xl">
          <div className="absolute inset-0 bg-black/10" />
          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h1 className="text-2xl md:text-4xl font-bold text-white tracking-tight">
                STOM <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 to-orange-400">트레이딩</span> 대시보드
              </h1>
              <p className="text-indigo-100 text-sm mt-1">실시간 시장 데이터 모니터링</p>
            </div>
            {/* 연결 상태 배지 */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur-sm ${
              connected
                ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                : 'bg-red-500/20 text-red-300 border border-red-500/30'
            }`}>
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
              <span className="text-sm font-medium">{connected ? '연결됨' : '연결 끊김'}</span>
            </div>
          </div>
        </div>

        {/* 컬러풀한 탭 네비게이션 */}
        <Tabs value={selectedMarket} onValueChange={(v) => setSelectedMarket(v as MarketType)}>
          <TabsList className="grid w-full grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 h-auto bg-slate-800/50 p-1 rounded-xl border border-slate-700/50">
            {MARKETS.map((market, index) => (
              <TabsTrigger
                key={market}
                value={market}
                className={`
                  text-xs sm:text-sm py-2.5 px-2 rounded-lg font-medium transition-all duration-300
                  whitespace-nowrap relative overflow-hidden
                  data-[state=active]:bg-gradient-to-r data-[state=active]:shadow-lg
                  ${index % 3 === 0 ? 'data-[state=active]:from-blue-500 data-[state=active]:to-cyan-500 data-[state=active]:text-white' : ''}
                  ${index % 3 === 1 ? 'data-[state=active]:from-purple-500 data-[state=active]:to-pink-500 data-[state=active]:text-white' : ''}
                  ${index % 3 === 2 ? 'data-[state=active]:from-orange-500 data-[state=active]:to-red-500 data-[state=active]:text-white' : ''}
                  data-[state=inactive]:text-slate-400 data-[state=inactive]:hover:text-slate-200
                  data-[state=inactive]:hover:bg-slate-700/50
                `}
              >
                {MARKET_NAMES[market]}
              </TabsTrigger>
            ))}
          </TabsList>

          {MARKETS.map((market) => (
            <TabsContent key={market} value={market} className="space-y-4 md:space-y-6 mt-4">
              {!connected && (
                <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 text-amber-300 p-4 rounded-xl text-sm flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                  서버 연결 중입니다...
                </div>
              )}

              {data && (
                <>
                  {/* 요약 카드 */}
                  <SummaryCards totalTrade={data.totaltradelist} />
                  <AlertPanel alerts={data.alerts || []} />

                  {/* 테이블 그리드 with glassmorphism */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
                    <JangoTable items={data.jangolist} />
                    <ChegeolTable items={data.chegeollist} />
                  </div>

                  <ProfitChart trades={data.tradelist} />
                  <TradeTable items={data.tradelist} />
                </>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  )
}
