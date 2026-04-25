
import random
import sqlite3
import numpy as np
from typing import Dict, List, Tuple
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static import now, thread_decorator


VOLUME_PROFILE_DB = f'{DB_PATH}/volume_profile.db'
window_queue = None


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


class AnalyzerVolumeProfile:
    """메인 볼륨 프로파일 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, top_nodes: int = 20):
        """
        초기화
        :param market_gubun: 마켓 구분 번호
        :param market_info: 마켓 정보 딕셔너리
        :param top_nodes: 상위 볼륨 노드 개수 (기본값 20)
        """
        self.backtest_db_path = market_info['백테디비'][0]
        self.factor_list      = market_info['팩터목록'][0]
        self.strategy_gubun   = market_info['전략구분']
        self.volume_database  = VolumeProfileDatabase(self.strategy_gubun)
        analysis_period, rate_threshold, price_range_pct = self.volume_database.load_volume_setting(market_gubun)
        self.analysis_period  = analysis_period
        self.rate_threshold   = round(rate_threshold / 100, 4)
        self.price_range_pct  = round(price_range_pct / 100, 4)
        self.top_nodes        = top_nodes
        self.volume_realtime  = VolumeProfileRealtime(self.factor_list, self.strategy_gubun, self.price_range_pct)

    def analyze_current_price(self, code: str, current_price: float) -> Dict[str, float]:
        """
        실시간 볼륨 프로파일 분석 수행
        :param code: 종목코드
        :param current_price: 현재 가격
        :return: 볼륨 프로파일 점수 정보
        """
        return self.volume_realtime.analyze_current_position(code, current_price)

    def train_all_codes(self, windowQ):
        """전체 종목 패턴 학습 수행 (종목 기반 멀티프로세싱)"""
        code_list     = self.get_code_list()
        num_processes = cpu_count()
        code_chunks   = self._split_codes(code_list, num_processes)

        actual_processes = min(num_processes, len(code_chunks))
        with Pool(processes=actual_processes, initializer=init_worker, initargs=(windowQ,)) as pool:
            args = [(i, chunk, self.backtest_db_path, self.factor_list, self.analysis_period,
                     self.rate_threshold, self.price_range_pct, self.top_nodes)
                    for i, chunk in enumerate(code_chunks)]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            for code, volume_scores in chunk_results.items():
                self.volume_database.save_volume_scores(code, volume_scores)
                total_processed += 1
            windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i + 1}/{actual_processes}]"))

        windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
        windowQ.put((UI_NUM['학습로그'], f"{VOLUME_PROFILE_DB} -> {self.volume_database.table_name}"))
        windowQ.put((UI_NUM['학습로그'], f"가격대분석 학습 완료 [{total_processed}]"))

    def get_code_list(self) -> List[str]:
        """
        백테 디비에서 종목코드 목록 추출
        :return: 종목코드 리스트
        """
        with sqlite3.connect(self.backtest_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]
            return code_list

    def _split_codes(self, code_list: List[str], num_chunks: int) -> List[List[str]]:
        """
        종목 리스트를 CPU수만큼 분할
        code_list: 종목코드 리스트
        num_chunks: 분할할 청크 수 (CPU 코어 수)
        return: 분할된 종목코드 청크 리스트
        """
        if len(code_list) <= num_chunks:
            return [[code] for code in code_list]

        chunk_size = len(code_list) // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(code_list)
            chunks.append(code_list[start:end])
        return chunks

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db_path: str, factor_list: list,
                          analysis_period: int, rate_threshold: float, price_range_pct: float,
                          top_nodes: int) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db_path: 백테디비 경로
        factor_list: 팩터 리스트
        analysis_period: 분석 기간
        rate_threshold: 등락율 임계값
        price_range_pct: 가격대 분할 퍼센트
        top_nodes: 상위 볼륨 노드 개수
        return: 종목별 패턴 점수 딕셔너리 {code: pattern_scores}
        """
        global window_queue
        volume_learning = \
            VolumeProfileLearning(factor_list, analysis_period, rate_threshold, price_range_pct, top_nodes)
        all_volume_scores = {}
        last = len(code_chunk)

        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                volume_scores = volume_learning.train_volume_profile(historical_data)
                if volume_scores:
                    all_volume_scores[code] = volume_scores
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 볼륨 프로파일 학습 중 ... [{k + 1}/{last}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 볼륨 프로파일 학습 실패 - {e}"))

        return all_volume_scores


class VolumeProfileLearning:
    """과거데이터 기반 볼륨 프로파일 학습 모듈"""
    def __init__(self, factor_list: list, analysis_period: int, rate_threshold: float,
                 price_range_pct: float, top_nodes: int):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param analysis_period: 분석 기간 분 (기본값 10)
        :param rate_threshold: 돌파/반등 판정 기준 퍼센트 (기본값 0.5)
        :param price_range_pct: 가격대 분할 퍼센트 (기본값 0.5)
        :param top_nodes: 상위 볼륨 노드 개수 (기본값 20)
        """
        self.idx_close       = factor_list.index('현재가')
        self.idx_volume      = factor_list.index('분당거래대금')
        self.analysis_period = analysis_period
        self.rate_threshold  = rate_threshold
        self.price_range_pct = price_range_pct
        self.top_nodes       = top_nodes

    def train_volume_profile(self, historical_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        종목별 과거데이터로 볼륨 프로파일 학습
        :param historical_data: 과거 1분봉 데이터 (2차원 numpy 어레이)
        :return: 가격대별 점수 딕셔너리
        """
        recent_data   = historical_data[-10000:] if len(historical_data) > 10000 else historical_data
        close_price   = recent_data[:, self.idx_close]
        volume_data   = recent_data[:, self.idx_volume]
        min_price     = close_price.min()
        max_price     = close_price.max()
        price_bins    = self._create_price_bins(min_price, max_price)
        volume_by_bin = self._aggregate_volume_by_price(close_price, volume_data, price_bins)
        volume_nodes  = self._identify_volume_nodes(price_bins, volume_by_bin)

        node_scores = {}
        for node_price in volume_nodes:
            upward_strength, downward_strength, sample_count = self._calculate_penetration_bounce_rate(
                close_price, node_price
            )

            if sample_count >= 10:
                score, confidence = self._calculate_score(upward_strength, downward_strength, sample_count)
                node_scores[node_price] = {
                    'avg_score': score,
                    'upward_strength': upward_strength,
                    'downward_strength': downward_strength,
                    'sample_count': sample_count,
                    'confidence_score': confidence
                }

        return node_scores

    def _create_price_bins(self, min_price: float, max_price: float) -> np.ndarray:
        """퍼센트 기반 가격대 분할"""
        bin_size = min_price * self.price_range_pct
        num_bins = int((max_price - min_price) / bin_size) + 1
        bins = np.linspace(min_price, max_price, num_bins)
        return bins

    def _aggregate_volume_by_price(self, close_price: np.ndarray, volume_data: np.ndarray, 
                                   price_bins: np.ndarray) -> np.ndarray:
        """각 가격대별 거래량 집계"""
        volume_by_bin = np.zeros(len(price_bins) - 1)
        for i in range(len(close_price)):
            price   = close_price[i]
            volume  = volume_data[i]
            bin_idx = np.digitize(price, price_bins) - 1
            if 0 <= bin_idx < len(volume_by_bin):
                volume_by_bin[bin_idx] += volume
        return volume_by_bin

    def _identify_volume_nodes(self, price_bins: np.ndarray, volume_by_bin: np.ndarray) -> List[float]:
        """상위 거래량 구간 식별"""
        bin_centers    = (price_bins[:-1] + price_bins[1:]) / 2
        sorted_indices = np.argsort(volume_by_bin)[::-1]
        top_indices    = sorted_indices[:self.top_nodes]
        volume_nodes   = [bin_centers[idx] for idx in top_indices]
        return volume_nodes

    def _calculate_penetration_bounce_rate(self, close_price: np.ndarray,
                                           node_price: float) -> Tuple[float, float, int]:
        """돌파/반등 확률 계산 (상방/하방 분리)"""
        upward_penetration = 0      # 상방 돌파
        downward_penetration = 0    # 하방 돌파
        bounce_up = 0               # 반등 후 상승
        bounce_down = 0             # 반등 후 하락
        total_count = 0

        threshold = node_price * self.rate_threshold

        for i in range(len(close_price) - self.analysis_period):
            price = close_price[i]

            if abs(price - node_price) / node_price <= self.rate_threshold:
                total_count += 1

                future_prices = close_price[i+1:i+1+self.analysis_period]

                if future_prices.max() >= node_price + threshold:
                    upward_penetration += 1
                elif future_prices.min() <= node_price - threshold:
                    downward_penetration += 1
                else:
                    # 반등 경우: 이후 10봉의 방향 확인
                    if future_prices[-1] > future_prices[0]:
                        bounce_up += 1
                    else:
                        bounce_down += 1

        if total_count == 0:
            return 0.0, 0.0, 0

        upward_strength   = (upward_penetration + bounce_up) / total_count
        downward_strength = (downward_penetration + bounce_down) / total_count

        return upward_strength, downward_strength, total_count

    def _calculate_score(self, upward_strength: float, downward_strength: float,
                         sample_count: int) -> Tuple[float, float]:
        """종합 점수 및 신뢰도 계산"""
        final_score = (upward_strength - downward_strength) * 100
        final_score = max(-100.0, min(100.0, final_score))
        confidence_score = min(1.0, sample_count / 100) if sample_count >= 10 else 0.0
        return final_score, confidence_score


class VolumeProfileRealtime:
    """실시간 볼륨 프로파일 분석 모듈"""
    def __init__(self, factor_list: list, strategy_gubun: str, price_range_pct: float):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param strategy_gubun: 전략 구분
        :param price_range_pct: 볼륨 노드 탐색 범위 퍼센트
        """
        self.idx_close       = factor_list.index('현재가')
        self.price_range_pct = price_range_pct
        self.volume_database = VolumeProfileDatabase(strategy_gubun)
        self.volume_nodes    = {}
        self._load_volume_nodes()

    def _load_volume_nodes(self):
        """데이터베이스에서 모든 종목의 볼륨 노드 로드"""
        all_codes = self.volume_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volume_nodes[code] = self.volume_database.get_all_volume_scores(code)

    def analyze_current_position(self, code: str, current_price: float) -> Dict[str, float]:
        """
        현재 가격 위치의 볼륨 프로파일 점수 반환
        :param code: 종목코드
        :param current_price: 현재 가격
        :return: 볼륨 프로파일 점수 및 신뢰도 정보
        """
        volume_profile_score, confidence_score = 0, 0

        if code in self.volume_nodes:
            nearest_node = self._find_nearest_volume_node(current_price, self.volume_nodes[code])
            if nearest_node:
                node_data = self.volume_nodes[code][nearest_node]
                volume_profile_score = node_data['avg_score']
                confidence_score = node_data['confidence_score']

        return volume_profile_score, confidence_score

    def _find_nearest_volume_node(self, current_price: float, volume_scores: Dict[str, Dict[str, float]]) -> float:
        """가장 가까운 볼륨 노드 탐색"""
        nearest_node = None
        min_distance = float('inf')

        for node_price in volume_scores.keys():
            distance = abs(current_price - node_price)
            if distance / node_price <= self.price_range_pct:
                if distance < min_distance:
                    min_distance = distance
                    nearest_node = node_price

        return nearest_node


class VolumeProfileDatabase:
    """볼륨 프로파일 점수 데이터베이스 관리 클래스"""

    def __init__(self, strategy_gubun: str):
        self.table_name = f'{strategy_gubun}_volume_score'
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS volume_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold REAL NOT NULL,
                    price_range_pct REAL NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    price_level REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    upward_strength REAL NOT NULL,
                    downward_strength REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    last_update TEXT NOT NULL,
                    PRIMARY KEY (code, price_level)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """데이터베이스에 저장된 전체 종목코드 조회"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_all_volume_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """종목의 전체 볼륨 프로파일 점수 조회"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT price_level, avg_score, upward_strength, downward_strength, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ?
            ''', (code,))
            results = cursor.fetchall()

            volume_scores = {}
            for result in results:
                volume_scores[result[0]] = {
                    'avg_score': result[1],
                    'upward_strength': result[2],
                    'downward_strength': result[3],
                    'sample_count': result[4],
                    'confidence_score': result[5]
                }
            return volume_scores

    def save_volume_scores(self, code: str, volume_scores: Dict[str, Dict[str, float]]):
        """종목별 볼륨 프로파일 점수 저장"""
        current_date = now().strftime('%Y-%m-%d')

        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            for price_level, scores in volume_scores.items():
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {self.table_name} 
                    (code, price_level, avg_score, upward_strength, downward_strength, sample_count,
                    confidence_score, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    price_level,
                    scores['avg_score'],
                    scores['upward_strength'],
                    scores['downward_strength'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    current_date
                ))
            conn.commit()

    def load_volume_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (price_range_pct, rate_threshold) 튜플, 데이터가 없으면 (30, 10) 반환
        """
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, rate_threshold, price_range_pct FROM volume_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if result:
                return result
            return 0.5, 0.5, 20

    def save_volume_setting(self, market: int, analysis_period: int, rate_threshold: float, price_range_pct: float):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석기간설정
        rate_threshold: 퍼센트설정
        price_range_pct: 분봉설정
        """
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO volume_setting (market, analysis_period, rate_threshold, price_range_pct)'
                'VALUES (?, ?, ?)',
                (market, analysis_period, rate_threshold, price_range_pct)
            )
            conn.commit()


def volume_setting_load(ui):
    """두개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    volume_database = VolumeProfileDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, price_range_pct = volume_database.load_volume_setting(ui.market_gubun)
    ui.vpf_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vpf_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vpf_comboBoxxx_03.setCurrentText(str(price_range_pct))


def volume_setting_save(ui):
    """두개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period = int(ui.vpf_comboBoxxx_01.currentText())
    rate_threshold  = float(ui.vpf_comboBoxxx_02.currentText())
    price_range_pct = float(ui.vpf_comboBoxxx_03.currentText())
    volume_database = VolumeProfileDatabase(ui.market_info['전략구분'])
    volume_database.save_volume_setting(ui.market_gubun, analysis_period, rate_threshold, price_range_pct)
    QMessageBox.information(ui.dialog_volume, '저장완료', random.choice(famous_saying))


def volume_profile_train(ui):
    """볼륨 프로파일 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_volume, '오류 알림', '현재 볼륨 프로파일 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vpf_comboBoxxx_01.currentText())
    _rate_threshold  = float(ui.vpf_comboBoxxx_02.currentText())
    _price_range_pct = float(ui.vpf_comboBoxxx_03.currentText())
    volume_database = VolumeProfileDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, price_range_pct = volume_database.load_volume_setting(ui.market_gubun)
    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _price_range_pct != price_range_pct:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _volume_profile_train(ui)


@thread_decorator
def _volume_profile_train(ui):
    """스레드로 볼륨 프로파일 학습을 시작한다."""
    ui.learn_running = True
    vf_analyzer = AnalyzerVolumeProfile(ui.market_gubun, ui.market_info)
    vf_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
