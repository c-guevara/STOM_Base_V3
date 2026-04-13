
from trade.base_strategy import BaseStrategy
from utility.static_method.static import get_profit_stock, now, dt_ymdhms, get_hogaunit_stock


class StockStrategy(BaseStrategy):
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _update_globals_func(self, dict_add_func):
        globals().update(dict_add_func)

    def _get_hogaunit(self, 주문가격또는종목코드):
        return get_hogaunit_stock(주문가격또는종목코드)

    def _get_profit(self, 매입금액, 보유금액):
        return get_profit_stock(매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        return (now() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        return int((now() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        return int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        return int(거래금액 / 주문수량 + 0.5) if 주문수량 != 0 else 0
