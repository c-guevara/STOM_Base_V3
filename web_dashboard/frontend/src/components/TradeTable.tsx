import React from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { TradeItem } from '../types'

interface Props {
  items: TradeItem[]
}

function TradeTable({ items }: Props) {
  return (
    <Card>
      <CardHeader className="p-3 md:p-6">
        <CardTitle className="text-base md:text-xl">거래 내역</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-6 overflow-x-auto">
        <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs md:text-sm">종목명</TableHead>
                <TableHead className="text-xs md:text-sm">수익률</TableHead>
                <TableHead className="text-xs md:text-sm">수익금</TableHead>
                <TableHead className="text-xs md:text-sm">체결시간</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={`${item.종목명}-${item.체결시간}`}>
                  <TableCell className="font-medium text-xs md:text-sm">{item.종목명}</TableCell>
                  <TableCell className={`text-xs md:text-sm ${item.수익률 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {item.수익률.toFixed(2)}%
                  </TableCell>
                  <TableCell className={`text-xs md:text-sm ${item.수익금 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {item.수익금.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-xs md:text-sm">
                    {(() => {
                      if (!item.체결시간) return '-'
                      try {
                        let date: Date
                        // YYYYMMDDHHMMSS 형식인 경우
                        if (item.체결시간.length === 14 && /^\d+$/.test(item.체결시간)) {
                          const year = item.체결시간.substring(0, 4)
                          const month = item.체결시간.substring(4, 6)
                          const day = item.체결시간.substring(6, 8)
                          const hour = item.체결시간.substring(8, 10)
                          const minute = item.체결시간.substring(10, 12)
                          const second = item.체결시간.substring(12, 14)
                          date = new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`)
                        } else {
                          date = new Date(item.체결시간)
                        }
                        if (isNaN(date.getTime())) return '-'
                        return date.toLocaleTimeString('ko-KR', {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                          hour12: false
                        })
                      } catch {
                        return '-'
                      }
                    })()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
      </CardContent>
    </Card>
  )
}

export default React.memo(TradeTable)
