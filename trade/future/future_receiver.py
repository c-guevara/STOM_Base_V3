
import pandas as pd
from PyQt5.QtCore import QTimer
from traceback import format_exc
from utility.static import now, str_hms
from trade.base_receiver import BaseReceiver
from utility.setting_base import ui_num, DICT_CODE_INFO_TNAME
from trade.restapi_ls import LsRestAPI, LsRestData, WebSocketReceiver


class FutureReceiver(BaseReceiver):
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        """
        super().__init__(qlist, dict_set)

        self.teleQ = qlist[3]

        self.ls = LsRestAPI(self.windowQ, self.access, self.secret)
        self.token = self.ls.create_token()

        self._get_code_info()

        self.ws_thread = WebSocketReceiver(self.market_name, self.token, self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.scheduler)
        self.qtimer.start()

    def _get_code_info(self):
        dict_info, self.codes = self.ls.get_code_info_future()
        self.dict_name = {code: dict_info[code]['종목명'] for code in self.codes}
        dict_code = {name: code for code, name in self.dict_name.items()}

        self.windowQ.put((ui_num['종목명데이터'], self.dict_name, dict_code))
        self.traderQ.put(('종목정보', (self.dict_sgbn, self.dict_name)))

        df = pd.DataFrame.from_dict(dict_info, orient='index')
        self.queryQ.put(('종목디비', df, DICT_CODE_INFO_TNAME[self.market_gubun], 'replace'))

        text = f'{self.market_name} 시스템을 시작하였습니다.'
        self.teleQ.put(text)
        if self.dict_set['알림소리']: self.soundQ.put(text)
        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 리시버 시작'))

    def _convert_real_data(self, data):
        start = now()
        tr_cd = data['header']['tr_cd']
        body  = data['body']
        if body is None:
            return

        if tr_cd == self.tr_cd_hoga:
            try:
                dt = int(f"{self.str_today}{body['hotime']}")
                if self.dict_set['전략종료시간'] < int(str(dt)[8:]):
                    return
                code = body['symbol']
                name = self.dict_name[code]
                hoga_seprice = [
                    float(body['offerho1']), float(body['offerho2']), float(body['offerho3']),
                    float(body['offerho4']), float(body['offerho5'])
                ]
                hoga_buprice = [
                    float(body['bidho1']), float(body['bidho2']), float(body['bidho3']),
                    float(body['bidho4']), float(body['bidho5'])
                ]
                hoga_samount = [
                    float(body['offerrem1']), float(body['offerrem2']), float(body['offerrem3']),
                    float(body['offerrem4']), float(body['offerrem5'])
                ]
                hoga_bamount = [
                    int(body['bidrem1']), int(body['bidrem2']), int(body['bidrem3']),
                    int(body['bidrem4']), int(body['bidrem5'])
                ]
                hoga_tamount = [
                    int(body['totofferrem']), int(body['totbidrem'])
                ]
                self.update_hoga_data(dt, code, name, hoga_seprice, hoga_buprice, hoga_samount,
                                      hoga_bamount, hoga_tamount, start)
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - tr_cd_hoga'))

        elif tr_cd == self.tr_cd_trade:
            try:
                dt = int(f"{self.str_today}{body['chetime']}")
                if self.dict_set['전략종료시간'] < int(str(dt)[8:]):
                    return
                code  = body['symbol']
                c     = float(body['price'])
                o     = float(body['open'])
                h     = float(body['high'])
                low   = float(body['low'])
                v     = float(body['cvolume'])
                per   = float(body['drate'])
                dm    = int(body['value'])
                cg    = body['cgubun']
                tbids = int(body['msvolume'])
                tasks = int(body['mdvolume'])
                ch    = float(body['cpower'])
                self.update_tick_data(dt, code, c, o, h, low, v, per, dm, cg, tbids, tasks, ch)
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - tr_cd_trade'))

        elif tr_cd == self.tr_cd_oper:
            try:
                if body['jangubun'] == self.oper_gubun:
                    operation = int(body['jstatus'])
                    if operation in LsRestData.장운영상태:
                        self.operation = operation
                        self.soundQ.put(LsRestData.장운영상태[self.operation])
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - tr_cd_oper'))

    def scheduler(self):
        self.money_top_search()

        inthmsutc = int(str_hms())
        A = self.dict_set['전략종료시간'] < inthmsutc < self.dict_set['전략종료시간'] + 10 and \
            self.dict_set['프로세스종료']
        B = 160000 < inthmsutc < 160010
        if not self.dict_bool['프로세스종료'] and (A or B):
            self.receiver_process_kill()

        current_gsjm = tuple(self.list_gsjm)
        if current_gsjm != self.last_gsjm:
            for q in self.stgQs:
                q.put(('관심목록', current_gsjm))
            self.last_gsjm = current_gsjm
