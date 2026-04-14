
from ui.etcetera.etc import chart_clear
from ui.draw_chart.draw_chart_base import DrawChartBase
from utility.static_method.static import error_decorator
from utility.static_method.static import from_timestamp, dt_ymdhms
from ui.etcetera.process_alive import strategy_process_alive, receiver_process_alive


class DrawRealChart(DrawChartBase):
    """실시간 차트 그리기 클래스입니다.
    실시간 데이터를 사용하여 차트를 그립니다.
    """
    @error_decorator
    def draw_real_chart(self, data):
        """실시간 차트를 그립니다.
        Args:
            data: 차트 데이터 튜플
        """
        self.real = True
        self.code, self.ui.ctpg_arry = data[1:]

        if not self.ui.dialog_chart.isVisible():
            chart_clear(self.ui)
            if receiver_process_alive(self.ui):
                self.ui.receivQ.put(('차트종목코드', None))
            if strategy_process_alive(self.ui):
                if self.ui.market_gubun < 5:
                    for q in self.ui.stgQs:
                        q.put(('차트종목코드', None))
                else:
                    self.ui.stgQs[0].put(('차트종목코드', None))
            return

        self.chart_cnt = len(self.ui.ctpg)
        self.is_min = self.chart_cnt in (6, 8) or (self.chart_cnt == 10 and self.ui.ct_pushButtonnn_05.text() == 'CHART III')

        curr_last_index = self.ui.ctpg_arry[-1, 0]
        self.same_code = self.ui.ctpg_code == self.code
        self.same_time = self.last_index == curr_last_index

        if not (self.same_code and self.same_time):
            if self.is_min:
                self.ui.ctpg_xticks = [dt_ymdhms(f'{str(int(x))}00').timestamp() for x in self.ui.ctpg_arry[:, 0]]
            else:
                self.ui.ctpg_xticks = [dt_ymdhms(str(int(x))).timestamp() for x in self.ui.ctpg_arry[:, 0]]
        else:
            if self.is_min:
                self.ui.ctpg_xticks.append(dt_ymdhms(f'{str(int(curr_last_index))}00').timestamp())
            else:
                self.ui.ctpg_xticks.append(dt_ymdhms(str(int(curr_last_index))).timestamp())

        self.last_index = curr_last_index
        self.gsjm_arry = self.ui.ctpg_arry[:, self.fi('관심종목')]
        self.xmin, self.xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        self.hms = from_timestamp(self.xmax).strftime('%H:%M' if self.is_min else '%H:%M:%S')

        self.draw_all_chart()
