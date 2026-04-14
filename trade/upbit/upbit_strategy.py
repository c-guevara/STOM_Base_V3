
from trade.base_strategy import BaseStrategy
from utility.static_method.static import get_profit_coin, now_utc, dt_ymdhms, get_hogaunit_coin


class UpbitStrategy(BaseStrategy):
    """업비트 전략 클래스입니다.
    
    BaseStrategy를 상속받아 업비트 시장 전략을 실행합니다.
    """
    
    def __init__(self, gubun, qlist, dict_set, market_info):
        """전략을 초기화합니다.
        
        Args:
            gubun (int): 구분 번호
            qlist (list): 큐 리스트
            dict_set (dict): 설정 딕셔너리
            market_info (list): 마켓 정보 리스트
        """
        super().__init__(gubun, qlist, dict_set, market_info)

    def _update_globals_func(self, dict_add_func):
        """전역 함수를 업데이트합니다.
        
        Args:
            dict_add_func (dict): 추가할 전역 함수 딕셔너리
        """
        globals().update(dict_add_func)

    def _get_hogaunit(self, 주문가격):
        """호가 단위를 반환합니다.
        
        Args:
            주문가격 (float): 주문 가격
            
        Returns:
            float: 호가 단위
        """
        return get_hogaunit_coin(주문가격)

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다.
        
        Args:
            매입금액 (float): 매입 금액
            보유금액 (float): 보유 금액
            
        Returns:
            tuple: (평가금액, 수익금, 수익률)
        """
        return get_profit_coin(매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다.
        
        Args:
            매수시간 (datetime): 매수 시간
            
        Returns:
            float: 보유 시간 (초)
        """
        return (now_utc() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        """보유 시간을 분 단위로 계산합니다.
        
        Args:
            매수시간 (datetime): 매수 시간
            
        Returns:
            int: 보유 시간 (분)
        """
        return int((now_utc() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다.
        
        Args:
            betting (float): 배팅 금액
            현재가 (float): 현재가
            매수가 (float): 매수가
            oc_ratio (float): 분할 비율
            
        Returns:
            float: 매수 수량
        """
        return round(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100, 8)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다.
        
        Args:
            보유수량 (float): 보유 수량
            보유비율 (float): 보유 비율
            oc_ratio (float): 분할 비율
            
        Returns:
            float: 매도 수량
        """
        return round(보유수량 / 보유비율 * oc_ratio, 8)

    def _get_order_price(self, 거래금액, 주문수량):
        return round(거래금액 / 주문수량, 4) if 주문수량 != 0 else 0
