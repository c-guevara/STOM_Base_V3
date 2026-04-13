
from backtest.future.backengine_future_oms import BackEngineFutureOms
from utility.static_method.static import get_profit_future_os_long, get_profit_future_os_short


class BackEngineFutureOverseaOms(BackEngineFutureOms):
    def _get_hogaunit(self, 주문가격또는종목코드):
        return self.dict_info[주문가격또는종목코드]['호가단위']

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        return int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        return round(거래금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])

    def _get_last_sell_price(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, self.dict_info[self.code]['소숫점자리수'])
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), self.dict_info[self.code]['소숫점자리수'])
        return 매도가

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 보유수량
        보유금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[self.code]['틱가치'] * 보유수량
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = get_profit_future_os_long(매입금액, 보유금액)
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = get_profit_future_os_short(매입금액, 보유금액)
        return 포지션, 평가금액, 수익금, 수익률
