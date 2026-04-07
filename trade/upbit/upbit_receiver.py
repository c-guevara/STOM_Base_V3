
from PyQt5.QtCore import QTimer
from traceback import format_exc
from utility.setting_base import ui_num
from trade.base_receiver import BaseReceiver
from utility.static import now, str_ymdhms_utc, str_hms, now_utc
from trade.upbit.upbit_restapi import WebSocketReceiver, get_symbols_info


class UpbitReceiver(BaseReceiver):
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        """
        super().__init__(qlist, dict_set)

        self.teleQ = qlist[3]

        self._get_code_info()

        self.ws_thread = WebSocketReceiver(self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.scheduler)
        self.qtimer.start()

    def _get_code_info(self):
        self.dict_daym, self.codes = get_symbols_info()
        self.list_gsjm = [x for x, y in sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:10]]
        data = tuple(self.list_gsjm)
        self.stgQ.put(('관심목록', data))

        text = f'{self.market_name} 시스템을 시작하였습니다.'
        self.teleQ.put(text)
        if self.dict_set['알림소리']: self.soundQ.put(text)
        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 리시버 시작'))

    def _convert_real_data(self, data):
        try:
            if data['type'] == 'orderbook':
                dt = int(str_ymdhms_utc(data['timestamp']))
                if self.dict_set['전략종료시간'] < int(str(dt)[8:]):
                    return
                receivetime = now()
                code = data['code']
                hoga_tamount = [
                    data['total_ask_size'], data['total_bid_size']
                ]
                data = data['orderbook_units']
                hoga_seprice = [
                    data[0]['ask_price'], data[1]['ask_price'], data[2]['ask_price'], data[3]['ask_price'],
                    data[4]['ask_price'], data[5]['ask_price'], data[6]['ask_price'], data[7]['ask_price'],
                    data[8]['ask_price'], data[9]['ask_price']
                ]
                hoga_buprice = [
                    data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'],
                    data[4]['bid_price'], data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'],
                    data[8]['bid_price'], data[9]['bid_price']
                ]
                hoga_samount = [
                    data[0]['ask_size'], data[1]['ask_size'], data[2]['ask_size'], data[3]['ask_size'],
                    data[4]['ask_size'], data[5]['ask_size'], data[6]['ask_size'], data[7]['ask_size'],
                    data[8]['ask_size'], data[9]['ask_size']
                ]
                hoga_bamount = [
                    data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'],
                    data[4]['bid_size'], data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'],
                    data[8]['bid_size'], data[9]['bid_size']
                ]
                self.update_hoga_data(dt, code, code, hoga_seprice, hoga_buprice, hoga_samount,
                                      hoga_bamount, hoga_tamount, receivetime)
            else:
                dt = int(str_ymdhms_utc(data['timestamp']))
                if self.dict_set['전략종료시간'] < int(str(dt)[8:]):
                    return
                code  = data['code']
                c     = data['trade_price']
                o     = data['opening_price']
                h     = data['high_price']
                low   = data['low_price']
                per   = round(data['signed_change_rate'] * 100, 2)
                dm    = data['acc_trade_price']
                tbids = data['acc_bid_volume']
                tasks = data['acc_ask_volume']
                self.update_tick_data_coin(dt, code, c, o, h, low, per, dm, tbids, tasks)
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - _convert_real_data'))

    def scheduler(self):
        self.money_top_search()

        inthmsutc = int(str_hms(now_utc()))
        A = self.dict_set['전략종료시간'] < inthmsutc < self.dict_set['전략종료시간'] + 10 and \
            self.dict_set['프로세스종료']
        B = 235000 < inthmsutc < 235010
        if not self.dict_bool['프로세스종료'] and (A or B):
            self.receiver_process_kill()

        current_gsjm = tuple(self.list_gsjm)
        if current_gsjm != self.last_gsjm:
            self.stgQ.put(('관심목록', current_gsjm))
            self.last_gsjm = current_gsjm
