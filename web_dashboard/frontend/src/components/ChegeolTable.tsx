import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { ChegeolItem } from '../types'

interface Props {
  items: ChegeolItem[]
}

export default function ChegeolTable({ items }: Props) {
  return (
    <Card>
      <CardHeader className="p-3 md:p-6">
        <CardTitle className="text-base md:text-xl">실시간 체결 내역</CardTitle>
      </CardHeader>
      <CardContent className="p-0 md:p-6">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs md:text-sm">종목명</TableHead>
                <TableHead className="text-xs md:text-sm">주문구분</TableHead>
                <TableHead className="text-xs md:text-sm">체결가</TableHead>
                <TableHead className="text-xs md:text-sm">체결수량</TableHead>
                <TableHead className="text-xs md:text-sm hidden sm:table-cell">체결시간</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.index}>
                  <TableCell className="font-medium text-xs md:text-sm">{item.종목명}</TableCell>
                  <TableCell className={`text-xs md:text-sm ${['매수', 'BUY_LONG', 'SELL_SHORT'].includes(item.주문구분) ? 'text-red-600' : ['매도', 'SELL_LONG', 'BUY_SHORT'].includes(item.주문구분) ? 'text-blue-600' : ''}`}>{item.주문구분}</TableCell>
                  <TableCell className="text-xs md:text-sm">{item.체결가.toLocaleString()}</TableCell>
                  <TableCell className="text-xs md:text-sm">{item.체결수량}</TableCell>
                  <TableCell className="text-xs md:text-sm hidden sm:table-cell">{item.체결시간}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
