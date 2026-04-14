
from ui.etcetera.etc import chart_clear
from PyQt5.QtWidgets import QMessageBox
from utility.static_method.static import from_timestamp
from ui.draw_chart.draw_chart_base import DrawChartBase
from utility.static_method.static import error_decorator
from ui.event_click.button_clicked_etc import hg_button_clicked_02


class DrawDBChart(DrawChartBase):
    """DB 차트 그리기 클래스입니다.
    데이터베이스에서 읽어온 데이터를 사용하여 차트를 그립니다.
    """
    @error_decorator
    def draw_db_chart(self, data):
        """DB 차트를 그립니다.
        Args:
            data: 차트 데이터 튜플
        """
        self.real = False
        chart_clear(self.ui)
        if not self.ui.dialog_chart.isVisible():
            return

        if data[1] == '차트오류':
            QMessageBox.critical(self.ui.dialog_chart, '오류 알림', '해당 날짜의 데이터가 존재하지 않습니다.\n')
            return

        self.ui.ctpg_xticks, self.ui.ctpg_arry, self.ui.buy_index, self.ui.sell_index, \
            fm_list, dict_fm, fm_tcnt = data[1:]

        if self.ui.trading:
            QMessageBox.critical(self.ui.dialog_chart, '오류 알림', '매매 중에는 DB차트를 볼 수 없습니다.\n')
            return

        if dict_fm:
            self.ui.fm_list = fm_list
            self.ui.dict_fm = dict_fm
        else:
            self.ui.fm_list = []
            self.ui.dict_fm = None

        self.code = self.ui.ct_lineEdittttt_04.text()
        self.chart_cnt = len(self.ui.ctpg)
        self.is_min = self.chart_cnt in (6, 8) or (self.chart_cnt == 10 and self.ui.ct_pushButtonnn_05.text() == 'CHART III')

        self.gsjm_arry = self.ui.ctpg_arry[:, self.fi('관심종목')]
        self.xmin, self.xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        self.hms = from_timestamp(self.xmax).strftime('%H:%M' if self.is_min else '%H:%M:%S')
        self.same_time = False

        self.draw_all_chart()

        if self.ui.dialog_hoga.isVisible() and self.ui.hg_labellllllll_01.text():
            hg_button_clicked_02(self.ui, '매수')
