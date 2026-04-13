
from trade.base_strategy import BaseStrategy
from utility.static_method.static import now_utc, dt_ymdhms, get_profit_coin_future_short, get_profit_coin_future_long


class BinanceStrategy(BaseStrategy):
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _update_globals_func(self, dict_add_func):
        globals().update(dict_add_func)

    def _get_hogaunit(self, 주문가격또는종목코드):
        return self.dict_info[주문가격또는종목코드]['호가단위']

    def _get_profit_long(self, 매입금액, 보유금액):
        return get_profit_coin_future_long(
            매입금액, 보유금액, '시장가' in self.dict_set['매수주문유형'], '시장가' in self.dict_set['매도주문유형']
        )

    def _get_profit_short(self, 매입금액, 보유금액):
        return get_profit_coin_future_short(
            매입금액, 보유금액, '시장가' in self.dict_set['매수주문유형'], '시장가' in self.dict_set['매도주문유형']
        )

    def _get_hold_time(self, 매수시간):
        return (now_utc() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        return int((now_utc() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100, 소숫점자리수)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(보유수량 / 보유비율 * oc_ratio, 소숫점자리수)

    def _get_order_price(self, 거래금액, 주문수량):
        소숫점자리수 = self.dict_info[self.code]['가격소숫점자리수']
        return round(거래금액 / 주문수량, 소숫점자리수) if 주문수량 != 0 else 0.0
