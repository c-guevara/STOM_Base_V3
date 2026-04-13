
from backtest.future.backengine_future_oms import BackEngineFutureOms
from utility.static_method.static import get_profit_coin_future_long, get_profit_coin_future_short


class BackEngineBinanceOms(BackEngineFutureOms):
    def _get_hogaunit(self, 호가빼기데이터):
        return min(x for x in 호가빼기데이터 if x > 0)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100, 소숫점자리수)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(보유수량 / 보유비율 * oc_ratio, 소숫점자리수)

    def _get_order_price(self, 거래금액, 주문수량):
        소숫점자리수 = self.dict_info[self.code]['가격소숫점자리수']
        return round(거래금액 / 주문수량, 소숫점자리수) if 주문수량 != 0 else 0.0

    def _get_last_sell_price(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, 4)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), 4)
        return 매도가

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = get_profit_coin_future_long(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['매수주문유형'],
                '시장가' in self.dict_set['매도주문유형'])
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = get_profit_coin_future_short(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['매수주문유형'],
                '시장가' in self.dict_set['매도주문유형'])
        return 포지션, 평가금액, 수익금, 수익률
