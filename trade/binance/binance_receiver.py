
import re
import binance
from traceback import format_exc
from utility.setting_base import ui_num
from trade.base_receiver import BaseReceiver
from trade.binance.binance_websocket import WebSocketReceiver
from utility.static import now, str_ymdhms_utc, now_utc, str_ymd


class BinanceReceiver(BaseReceiver):
    def __init__(self, qlist, dict_set, market_info):
        super().__init__(qlist, dict_set, market_info)

        self.binance = binance.Client()

        self._get_code_info()
        self._start_notification()

        self.ws_thread = WebSocketReceiver(self.codes, self.windowQ)
        self.ws_thread.signal1.connect(self._convert_tick_data)
        self.ws_thread.signal2.connect(self._convert_hoga_data)
        self.ws_thread.start()

    def _get_code_info(self):
        dict_daym = {}
        datas = self.binance.futures_ticker()
        datas = [data for data in datas if re.search('USDT$', data['symbol']) is not None]
        ymd   = str_ymd(now_utc())
        for data in datas:
            code = data['symbol']
            if code not in self.dict_data:
                c    = float(data['lastPrice'])
                o    = float(data['openPrice'])
                h    = float(data['highPrice'])
                low  = float(data['lowPrice'])
                per  = round(float(data['priceChangePercent']), 2)
                dm   = float(data['quoteVolume'])
                prec = round(c - float(data['priceChange']), 8)
                self.dict_data[code] = [c, o, h, low, per, dm, 0, 0, 0, 0, 0, c, c, c]
                self.dict_prec[code] = [ymd, prec]
                dict_daym[code] = dm

        self.codes = list(self.dict_data)
        self.list_gsjm = [x for x, y in sorted(dict_daym.items(), key=lambda x: x[1], reverse=True)[:10]]
        data = tuple(self.list_gsjm)
        self.stgQ.put(('관심목록', data))

    def _convert_hoga_data(self, data):
        try:
            data = data['data']
            dt = int(str_ymdhms_utc(data['T']))
            if self.dict_set['전략종료시간'] < int(str(dt)[8:]):
                return
            receivetime = now()
            code = data['s']
            asks_data = data['a']
            bids_data = data['b']
            hoga_seprice = [
                float(asks_data[0][0]), float(asks_data[1][0]), float(asks_data[2][0]), float(asks_data[3][0]),
                float(asks_data[4][0]), float(asks_data[5][0]), float(asks_data[6][0]), float(asks_data[7][0]),
                float(asks_data[8][0]), float(asks_data[9][0])
            ]
            hoga_buprice = [
                float(bids_data[0][0]), float(bids_data[1][0]), float(bids_data[2][0]), float(bids_data[3][0]),
                float(bids_data[4][0]), float(bids_data[5][0]), float(bids_data[6][0]), float(bids_data[7][0]),
                float(bids_data[8][0]), float(bids_data[9][0])
            ]
            hoga_samount = [
                float(asks_data[0][1]), float(asks_data[1][1]), float(asks_data[2][1]), float(asks_data[3][1]),
                float(asks_data[4][1]), float(asks_data[5][1]), float(asks_data[6][1]), float(asks_data[7][1]),
                float(asks_data[8][1]), float(asks_data[9][1])
            ]
            hoga_bamount = [
                float(bids_data[0][1]), float(bids_data[1][1]), float(bids_data[2][1]), float(bids_data[3][1]),
                float(bids_data[4][1]), float(bids_data[5][1]), float(bids_data[6][1]), float(bids_data[7][1]),
                float(bids_data[8][1]), float(bids_data[9][1])
            ]
            hoga_tamount = [
                round(sum(hoga_samount), 8), round(sum(hoga_bamount), 8)
            ]
            self._update_hoga_data(dt, code, hoga_seprice, hoga_buprice, hoga_samount,
                                   hoga_bamount, hoga_tamount, receivetime)
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - convert_hoga_data'))

    def _convert_tick_data(self, data):
        try:
            data = data['data']
            dt   = int(str_ymdhms_utc(data['T']))
            code = data['s']
            c    = float(data['p'])
            v    = float(data['q'])
            m    = data['m']
            self._update_tick_data_coin_future(dt, code, c, v, m)
        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - convert_tick_data'))
