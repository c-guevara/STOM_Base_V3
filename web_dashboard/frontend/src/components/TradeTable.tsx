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
                  <TableCell className="text-xs md:text-sm">{item.체결시간}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
      </CardContent>
    </Card>
  )
}

export default React.memo(TradeTable)
