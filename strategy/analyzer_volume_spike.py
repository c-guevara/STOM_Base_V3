
import random
import sqlite3
import numpy as np
from typing import Dict, List
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static import now, thread_decorator


VOLUME_SPIKE_DB = f'{DB_PATH}/volume_spike.db'
window_queue = None


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


class AnalyzerVolumeSpike:
    """메인 거래량 급증 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, min_samples: int = 20):
        """
        초기화
        :param market_gubun: 마켓 구분 번호
        :param market_info: 마켓 정보 딕셔너리
        :param min_samples: 최소 샘플 수 (기본값 20)
        """
        self.backtest_db_path = market_info['백테디비'][0]
        self.factor_list      = market_info['팩터목록'][0]
        self.strategy_gubun   = market_info['전략구분']
        self.spike_database   = VolumeSpikeDatabase(self.strategy_gubun)
        analysis_period, rate_threshold, ratio_threshold = self.spike_database.load_spike_setting(market_gubun)
        self.analysis_period  = analysis_period
        self.rate_threshold   = rate_threshold
        self.ratio_threshold  = ratio_threshold
        self.min_samples      = min_samples
        self.spike_realtime   = \
            VolumeSpikeRealtime(self.factor_list, self.strategy_gubun, analysis_period, rate_threshold)

    def analyze_current_spike(self, code: str, realtime_data: np.ndarray) -> Dict[str, float]:
        """
        실시간 거래량 급증 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
        :return: 급증 분석 결과
        """
        return self.spike_realtime.analyze_current_spike(code, realtime_data)

    def train_all_codes(self, windowQ):
        """전체 종목 패턴 학습 수행 (종목 기반 멀티프로세싱)"""
        code_list     = self.get_code_list()
        num_processes = cpu_count()
        code_chunks   = self._split_codes(code_list, num_processes)

        actual_processes = min(num_processes, len(code_chunks))
        with Pool(processes=actual_processes, initializer=init_worker, initargs=(windowQ,)) as pool:
            args = [(i, chunk, self.backtest_db_path, self.factor_list, self.analysis_period,
                     self.rate_threshold, self.ratio_threshold, self.min_samples)
                    for i, chunk in enumerate(code_chunks)]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            for code, spike_scores in chunk_results.items():
                self.spike_database.save_spike_scores(code, spike_scores)
                total_processed += 1
            windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i + 1}/{actual_processes}]"))

        windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
        windowQ.put((UI_NUM['학습로그'], f"{VOLUME_SPIKE_DB} -> {self.spike_database.table_name}"))
        windowQ.put((UI_NUM['학습로그'], f"거래량분석 학습 완료 [{total_processed}]"))

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
                          analysis_period: int, rate_threshold: int, ratio_threshold: int,
                          min_samples: int) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db_path: 백테디비 경로
        market_info: 마켓 정보 딕셔너리
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        ratio_threshold: 급증 임계값
        min_samples: 최소 샘플 수
        return: 종목별 급증 점수 딕셔너리 {code: spike_scores}
        """
        global window_queue
        spike_learning = \
            VolumeSpikeLearning(factor_list, analysis_period, rate_threshold, ratio_threshold, min_samples)
        all_spike_scores = {}
        last = len(code_chunk)
        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)
                spike_scores = spike_learning.train_volume_spikes(historical_data)
                if spike_scores:
                    all_spike_scores[code] = spike_scores
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 거래량 급증 패턴 학습 중 ... [{k + 1}/{last}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 거래량 급증 패턴 학습 실패 - {e}"))

        return all_spike_scores


class VolumeSpikeLearning:
    """과거데이터 기반 거래량 급증 패턴 학습 모듈"""
    def __init__(self, factor_list: list, analysis_period: int, rate_threshold: int,
                 ratio_threshold: int, min_samples: int):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param analysis_period: 분석 기간 분
        :param rate_threshold: 등락율 임계값
        :param ratio_threshold: 급증 임계값
        :param min_samples: 최소 샘플 수
        """
        self.idx_close       = factor_list.index('현재가')
        self.idx_volume      = factor_list.index('분당거래대금')
        self.analysis_period = analysis_period
        self.rate_threshold  = rate_threshold
        self.ratio_threshold = ratio_threshold
        self.min_samples     = min_samples

    def train_volume_spikes(self, historical_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        종목별 과거데이터로 거래량 급증 패턴 학습
        :param historical_data: 과거 1분봉 데이터 (2차원 numpy 어레이)
        :return: 급증 강도별 점수 딕셔너리
        """
        recent_data = historical_data[-10000:] if len(historical_data) > 10000 else historical_data
        close_price = recent_data[:, self.idx_close]
        volume_data = recent_data[:, self.idx_volume]

        ma_volume     = self._calculate_ma_volume(volume_data)
        spike_indices = self._detect_spikes(volume_data, ma_volume)

        spike_scores = {}
        spike_groups = self._group_spikes_by_multiplier(spike_indices, volume_data, ma_volume)

        for multiplier, indices in spike_groups.items():
            if len(indices) >= self.min_samples:
                scores = []
                for idx in indices:
                    if idx + self.analysis_period < len(close_price):
                        entry_price    = close_price[idx]
                        exit_max_price = close_price[idx:idx + self.analysis_period].max()
                        exit_min_price = close_price[idx:idx + self.analysis_period].min()
                        if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                            exit_price = exit_max_price
                        else:
                            exit_price = exit_min_price
                        price_change   = (exit_price - entry_price) / entry_price * 100
                        score          = self._calculate_score(price_change)
                        scores.append(score)

                if len(scores) >= self.min_samples:
                    confidence = self._calculate_confidence(len(scores), float(np.std(scores)))
                    spike_scores[multiplier] = {
                        'avg_score': float(np.mean(scores)),
                        'max_score': float(np.max(scores)),
                        'min_score': float(np.min(scores)),
                        'std_score': float(np.std(scores)),
                        'sample_count': len(scores),
                        'confidence_score': confidence
                    }

        return spike_scores

    def _calculate_ma_volume(self, volume_data: np.ndarray) -> np.ndarray:
        """이동평균 거래량 계산"""
        ma_volume = np.zeros(len(volume_data))
        for i in range(self.analysis_period, len(volume_data)):
            ma_volume[i] = np.mean(volume_data[i-self.analysis_period:i])
        return ma_volume

    def _detect_spikes(self, volume_data: np.ndarray, ma_volume: np.ndarray) -> List[int]:
        """급증 시점 탐지"""
        spike_indices = []
        for i in range(self.analysis_period, len(volume_data)):
            if ma_volume[i] > 0:
                multiplier = volume_data[i] / ma_volume[i]
                if multiplier >= self.rate_threshold:
                    spike_indices.append(i)
        return spike_indices

    def _group_spikes_by_multiplier(self, spike_indices: List[int], volume_data: np.ndarray,
                                    ma_volume: np.ndarray) -> Dict[float, List[int]]:
        """급증 강도별로 그룹화"""
        spike_groups = {}
        for idx in spike_indices:
            multiplier = volume_data[idx] / ma_volume[idx]
            rounded_multiplier = round(multiplier * 2) / 2
            if rounded_multiplier not in spike_groups:
                spike_groups[rounded_multiplier] = []
            spike_groups[rounded_multiplier].append(idx)
        return spike_groups

    def _calculate_score(self, price_change_percent: float) -> float:
        """가격변화율을 기반으로 점수 계산"""
        score = (price_change_percent / self.ratio_threshold) * 100
        return max(-100.0, min(100.0, score))

    def _calculate_confidence(self, sample_count: int, std_score: float) -> float:
        """신뢰도 계산"""
        sample_factor = min(sample_count / 100.0, 1.0)
        std_factor = max(1.0 - std_score / 50.0, 0.0)
        return (sample_factor + std_factor) / 2.0


class VolumeSpikeRealtime:
    """실시간 거래량 급증 분석 모듈"""
    def __init__(self, factor_list: list, strategy_gubun: str, analysis_period: int, rate_threshold: int):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param strategy_gubun: 전략 구분
        :param analysis_period: 분석 기간 분
        :param rate_threshold: 등락율 임계값
        """
        self.idx_volume      = factor_list.index('분당거래대금')
        self.analysis_period = analysis_period
        self.rate_threshold  = rate_threshold
        self.spike_database  = VolumeSpikeDatabase(strategy_gubun)
        self.spike_scores    = {}
        self._load_spike_scores()

    def _load_spike_scores(self):
        """데이터베이스에서 모든 종목의 급증 점수 로드"""
        all_codes = self.spike_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.spike_scores[code] = self.spike_database.get_all_spike_scores(code)

    def analyze_current_spike(self, code: str, realtime_data: np.ndarray) -> Dict[str, float]:
        """
        현재 거래량 급증 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터
        :return: 급증 분석 결과
        """
        is_spike = False
        spike_multiplier = 0.0
        spike_score = 0.0
        confidence = 0.0

        if len(realtime_data) >= self.analysis_period:
            volume_data    = realtime_data[:, self.idx_volume]
            ma_volume      = self._calculate_ma_volume(volume_data)
            current_volume = volume_data[-1]

            if ma_volume[-1] > 0:
                spike_multiplier = current_volume / ma_volume[-1]
                if spike_multiplier >= self.rate_threshold:
                    is_spike = True
                    rounded_multiplier = round(spike_multiplier * 2) / 2

                    if code in self.spike_scores and rounded_multiplier in self.spike_scores[code]:
                        score_data  = self.spike_scores[code][rounded_multiplier]
                        spike_score = score_data['avg_score']
                        confidence  = score_data['confidence_score']

        return {
            'is_spike': is_spike,
            'spike_multiplier': spike_multiplier,
            'score': spike_score,
            'confidence': confidence
        }

    def _calculate_ma_volume(self, volume_data: np.ndarray) -> np.ndarray:
        """이동평균 거래량 계산"""
        ma_volume = np.zeros(len(volume_data))
        for i in range(self.analysis_period, len(volume_data)):
            ma_volume[i] = np.mean(volume_data[i-self.analysis_period:i])
        return ma_volume


class VolumeSpikeDatabase:
    """거래량 급증 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str):
        self.table_name = f'{strategy_gubun}_volume_spike'
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS spike_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    ratio_threshold INTEGER NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    spike_multiplier REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    last_update TEXT NOT NULL,
                    PRIMARY KEY (code, spike_multiplier)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        :return: 종목코드 리스트
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_all_spike_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """
        종목의 전체 급증 점수 조회
        code: 종목코드
        return: 급증 강도별 점수 딕셔너리
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT spike_multiplier, avg_score, max_score, min_score, std_score, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ?
            ''', (code,))
            results = cursor.fetchall()

            spike_scores = {}
            for result in results:
                spike_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
            return spike_scores

    def save_spike_scores(self, code: str, spike_scores: Dict[str, Dict[str, float]]):
        """
        종목별 급증 점수 저장
        code: 종목코드
        spike_scores: 급증 강도별 점수 딕셔너리
        """
        current_date = now().strftime('%Y-%m-%d')

        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            for spike_multiplier, scores in spike_scores.items():
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {self.table_name} 
                    (code, spike_multiplier, avg_score, max_score, min_score, std_score, sample_count,
                    confidence_score, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    spike_multiplier,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    current_date
                ))
            conn.commit()

    def load_spike_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (analysis_period, rate_threshold, ratio_threshold) 튜플, 데이터가 없으면 (30, 3.0, 20) 반환
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, rate_threshold, ratio_threshold FROM spike_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if result:
                return result
            return 30, 5, 3

    def save_spike_setting(self, market: int, analysis_period: int, rate_threshold: float, ratio_threshold: int):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        ratio_threshold: 급증 임계값
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO spike_setting (market, analysis_period, rate_threshold, ratio_threshold) '
                'VALUES (?, ?, ?, ?)',
                (market, analysis_period, rate_threshold, ratio_threshold)
            )
            conn.commit()


def spike_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    spike_database = VolumeSpikeDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, ratio_threshold = spike_database.load_spike_setting(ui.market_gubun)
    ui.vsp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vsp_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vsp_comboBoxxx_03.setCurrentText(str(ratio_threshold))


def spike_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    ratio_threshold = int(ui.vsp_comboBoxxx_03.currentText())
    spike_database  = VolumeSpikeDatabase(ui.market_info['전략구분'])
    spike_database.save_spike_setting(ui.market_gubun, analysis_period, rate_threshold, ratio_threshold)
    QMessageBox.information(ui.dialog_spike, '저장완료', random.choice(famous_saying))


def spike_train(ui):
    """급증 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_spike, '오류 알림', '현재 급증 패턴 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    _ratio_threshold = int(ui.vsp_comboBoxxx_03.currentText())
    spike_database = VolumeSpikeDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, ratio_threshold = spike_database.load_spike_setting(ui.market_gubun)
    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _ratio_threshold != ratio_threshold:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _spike_train(ui)


@thread_decorator
def _spike_train(ui):
    """스레드로 급증 패턴 학습을 시작한다."""
    ui.learn_running = True
    vs_analyzer = AnalyzerVolumeSpike(ui.market_gubun, ui.market_info)
    vs_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
