import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TotalTrade } from '../types'
import { Wallet, TrendingUp, DollarSign, BarChart3 } from 'lucide-react'

interface Props {
  totalTrade: TotalTrade | null
}

export default function SummaryCards({ totalTrade }: Props) {
  if (!totalTrade) return null

  const cards = [
    { title: '총 평가금액', value: totalTrade.총매도금액.toLocaleString() + '원', color: 'text-blue-600', icon: Wallet },
    { title: '총 수익률', value: totalTrade.수익률.toFixed(2) + '%', color: totalTrade.수익률 >= 0 ? 'text-green-600' : 'text-red-600', icon: TrendingUp },
    { title: '총 수익금', value: totalTrade.수익금합계.toLocaleString() + '원', color: totalTrade.수익금합계 >= 0 ? 'text-green-600' : 'text-red-600', icon: DollarSign },
    { title: '거래 횟수', value: totalTrade.거래횟수.toString(), color: 'text-gray-600', icon: BarChart3 }
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <Card key={card.title} className="rounded-xl border border-border/40 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 shadow-lg hover:shadow-xl transition-all duration-200">
            <CardHeader className="pb-2 p-3 md:p-6 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-xs md:text-sm font-medium text-gray-600">{card.title}</CardTitle>
              <Icon className="w-4 h-4 text-gray-400" />
            </CardHeader>
            <CardContent className="p-3 md:p-6 pt-0">
              <div className={`text-lg md:text-2xl font-bold ${card.color}`}>
                {card.value}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
