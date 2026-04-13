
from backtest.backengine_base import BackEngineBase
from utility.static_method.static import get_hogaunit_coin, get_profit_coin


class BackEngineUpbit(BackEngineBase):
    def _update_globals_func(self, dict_add_func):
        globals().update(dict_add_func)

    def _get_hogaunit(self, 주문가격또는종목코드):
        return get_hogaunit_coin(주문가격또는종목코드)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        return round(betting / 현재가, 8)

    def _get_order_price(self, 거래금액, 주문수량):
        return round(거래금액 / 주문수량, 4)

    def _get_last_sell_price(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, 4)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), 4)
        return 매도가

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        시가총액 = 0
        평가금액, 수익금, 수익률 = get_profit_coin(보유수량 * 매수가, 보유수량 * 현재가)
        return 시가총액, 평가금액, 수익금, 수익률
