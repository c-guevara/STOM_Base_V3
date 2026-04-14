
import sys
from PyQt5.QtCore import QTimer
from trade.restapi_ls import LsRestAPI
from PyQt5.QtWidgets import QApplication
from trade.restapi_lsdata import LsRestData
from utility.settings.setting_base import ui_num
from trade.base_trader import BaseTrader, MonitorTraderQ
from utility.static_method.static import now, timedelta_sec, get_profit_future_os_long, get_profit_future_os_short


class FutureOsTrader(BaseTrader):
    """해외 선물 트레이더 클래스입니다.
    
    BaseTrader를 상속받아 해외 선물 시장 주문을 실행합니다.
    """
    
    def __init__(self, qlist, dict_set, market_infos):
        """트레이더를 초기화합니다.
        
        Args:
            qlist (list): 큐 리스트
            dict_set (dict): 설정 딕셔너리
            market_infos (list): 마켓 정보 리스트
        """
        super().__init__(qlist, dict_set, market_infos)

        app = QApplication(sys.argv)

        self.ls = LsRestAPI(self.windowQ, self.access_key, self.secret_key)
        self.token = self.ls.create_token()

        self._get_balances()

        if not self.dict_set['모의투자']:
            from trade.restapi_ls import LsWebSocketTrader
            self.ws_thread = LsWebSocketTrader(self.market_info['마켓이름'], self.token, self.windowQ)
            self.ws_thread.signal.connect(self._convert_order_data)
            self.ws_thread.start()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(500)
        self.qtimer1.timeout.connect(self._scheduler1)
        self.qtimer1.start()

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(1 * 1000)
        self.qtimer2.timeout.connect(self._scheduler2)
        self.qtimer2.start()

        self.updater = MonitorTraderQ(self.traderQ, self.market_gubun)
        self.updater.signal1.connect(self._check_order)
        self.updater.signal2.connect(self._check_order_future)
        self.updater.signal3.connect(self._update_tuple)
        self.updater.signal4.connect(self._update_string)
        self.updater.start()

        app.exec_()

    def _get_balances(self):
        if self.dict_set['모의투자']:
            yesugm = self._get_yesugm_for_paper_trading()
        else:
            yesugm = self.ls.get_balance_future_oversea()
        self._set_yesugm_and_noti(yesugm)

    def _send_order(self, data):
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self._send_order(data))
            return

        주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형 = data
        self._order_time_log(시그널시간)

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT', 'SELL_LONG', 'BUY_SHORT'):
            if 잔고청산:
                주문유형 = '시장가'
            else:
                if 수동주문유형 is None:
                    주문유형 = self.dict_set['매수주문유형' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도주문유형']
                else:
                    주문유형 = 수동주문유형

            """def order_future_oversea(self, 종목코드, 주문구분, 주문가격, 주문수량, 주문유형):"""
            od_no, msg = self.ls.order_future_oversea(종목코드, 주문구분, 주문가격, 주문수량, 주문유형)
            if od_no != '0':
                index = self._get_index()
                if 주문구분 == '매수':
                    self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                    add_time = self.dict_set['매수취소시간초']
                else:
                    add_time = self.dict_set['매도취소시간초']

                self.dict_order[주문구분][종목코드] = [
                    timedelta_sec(add_time), 정정횟수, 주문가격, 0.01
                ]

                self._update_chegeollist(
                    index, 종목코드, 종목명, f'{주문구분}접수', 주문수량, 0, 주문수량, 0, index[:14], 주문가격, od_no
                )

                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목명} | {주문가격} | {주문수량}'
                ))
            else:
                self._put_order_complete('매수취소', 종목코드)
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}실패] {종목명} | {주문가격} | {주문수량}'
                ))
                self.windowQ.put((ui_num['기본로그'], msg))

        elif 'MODIFY' in 주문구분:
            """def order_modify_future_oversea(self, 종목코드, 원주문번호, 주문구분, 주문가격, 주문수량, 주문유형):"""
            주문유형 = self.dict_set['매수주문유형' if 주문구분 in ('BUY_LONG_MODIFY', 'SELL_SHORT_MODIFY') else '매도주문유형']
            od_no, msg = self.ls.order_modify_future_oversea(종목코드, 원주문번호, 주문구분, 주문가격, 주문수량, 주문유형)
            if od_no == '0':
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}실패] {종목명} | {주문가격} | {주문수량}'
                ))
                self.windowQ.put((ui_num['기본로그'], msg))

        elif 'CANCEL' in 주문구분:
            """def order_cancel_future_oversea(self, 종목코드, 원주문번호):"""
            od_no, msg = self.ls.order_cancel_future_oversea(종목코드, 원주문번호)
            if od_no == '0':
                self.windowQ.put((
                    ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}실패] {종목명} | {주문가격} | {주문수량}'
                ))
                self.windowQ.put((ui_num['기본로그'], msg))

        self.order_time = timedelta_sec(0.2)
        self.receivQ.put(('주문목록', self._get_order_code_list()))

    def _convert_order_data(self, data):
        body = data['body']
        if body is None:
            return

        체결유형 = body['ordr_ccd']
        if 체결유형 in ('1', '2', '3'):
            체결구분 = LsRestData.선물주문체결코드[체결유형]
            종목코드 = body['is_cd']
            체결수량 = int(body['ccls_q'])
            체결가격 = float(body['ccls_prc'])
            체결시간 = f"{self.str_today}{int(int(body['ccls_tm']) / 1000)}"
            주문번호 = body['ordr_no']
            self._update_chejan_data_future(체결구분, 종목코드, 체결수량, 체결가격, 체결시간, 주문번호)

    def _get_order_buy_price(self, 종목코드, 주문구분, 주문가격):
        매수지정가호가번호 = self.dict_set['매수지정가호가번호']
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매수지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'BUY_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

    def _get_order_sell_price(self, 종목코드, 주문구분, 주문가격):
        매도지정가호가번호 = self.dict_set['매도지정가호가번호']
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매도지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'SELL_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

    def _get_modify_buy_price(self, 현재가, 정정호가, 종목코드):
        return round(현재가 - 정정호가, self.dict_info[종목코드]['소숫점자리수'])

    def _get_modify_sell_price(self, 현재가, 정정호가, 종목코드):
        return round(현재가 + 정정호가, self.dict_info[종목코드]['소숫점자리수'])

    def _get_profit_long(self, 매입금액, 보유금액):
        return get_profit_future_os_long(매입금액, 보유금액)

    def _get_profit_short(self, 매입금액, 보유금액):
        return get_profit_future_os_short(매입금액, 보유금액)

    def _get_hogaunit(self, 주문가격또는종목코드):
        return self.dict_info[주문가격또는종목코드]['호가단위']

    def _get_order_code_list(self):
        return tuple(self.dict_order['BUY_LONG']) + tuple(self.dict_order['SELL_SHORT']) + \
            tuple(self.dict_order['SELL_LONG']) + tuple(self.dict_order['BUY_SHORT'])
