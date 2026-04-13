
from backtest.backengine_base_oms import BackEngineBaseOms
from utility.static_method.static import get_profit_stock_os


class BackEngineStockUsaOms(BackEngineBaseOms):
    def _update_globals_func(self, dict_add_func):
        globals().update(dict_add_func)

    def _get_hogaunit(self, 주문가격또는종목코드):
        return 0.01

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        return int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        return round(거래금액 / 주문수량, 2)

    def _get_last_sell_price(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, 2)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), 2)
        return 매도가

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        시가총액 = int(self.arry_code[self.indexn, self.dict_findex['시가총액']])
        평가금액, 수익금, 수익률 = get_profit_stock_os(보유수량 * 매수가, 보유수량 * 현재가)
        return 시가총액, 평가금액, 수익금, 수익률
