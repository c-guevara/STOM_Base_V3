import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TotalTrade, MarketType } from '../types'
import { Wallet, TrendingUp, DollarSign, BarChart3, Clock } from 'lucide-react'

interface Props {
  totalTrade: TotalTrade | null
  market: MarketType
  timestamp?: string
}

export default function SummaryCards({ totalTrade, market, timestamp }: Props) {
  if (!totalTrade) return null

  // 거래소별 금액 단위 결정
  const currencyUnits: Record<MarketType, string> = {
    stock: '원',
    stock_etf: '원',
    stock_etn: '원',
    stock_usa: 'USD',
    future: '원',
    future_nt: '원',
    future_os: 'USD',
    coin: '원',
    coin_future: 'USDT'
  }

  const currency = currencyUnits[market]

  // 연월일 시간 포맷팅
  const formattedTimestamp = timestamp ? new Date(timestamp).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\./g, '').replace(/\//g, '') : ''

  const cards = [
    { title: '일자 시간', value: formattedTimestamp, color: 'text-gray-600', icon: Clock },
    { title: '거래 횟수', value: totalTrade.거래횟수.toString(), color: 'text-gray-600', icon: BarChart3 },
    { title: '총 매입금액', value: Math.floor(totalTrade.총매수금액).toLocaleString() + currency, color: 'text-blue-600', icon: Wallet },
    { title: '총 매도금액', value: Math.floor(totalTrade.총매도금액).toLocaleString() + currency, color: 'text-purple-600', icon: DollarSign },
    { title: '총 수익금', value: (totalTrade.수익금합계 >= 0 ? '+' : '') + Math.floor(totalTrade.수익금합계).toLocaleString() + currency, color: totalTrade.수익금합계 >= 0 ? 'text-red-600' : 'text-blue-600', icon: TrendingUp },
    { title: '총 수익률', value: (totalTrade.수익률 >= 0 ? '+' : '') + totalTrade.수익률.toFixed(2) + '%', color: totalTrade.수익률 >= 0 ? 'text-red-600' : 'text-blue-600', icon: TrendingUp }
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <Card key={card.title} className="rounded-xl border border-border/40 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 shadow-lg hover:shadow-xl transition-all duration-200">
            <CardHeader className="pb-2 p-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-xs font-medium text-gray-600">{card.title}</CardTitle>
              <Icon className="w-4 h-4 text-gray-400" />
            </CardHeader>
            <CardContent className="p-3 pt-0">
              <div className={`text-lg font-bold text-right ${card.color} ${card.title === '일자 시간' ? 'whitespace-nowrap' : ''}`}>
                {card.value}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
