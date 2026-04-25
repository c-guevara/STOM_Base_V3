
import random
import sqlite3
import numpy as np
from typing import Dict, List, Tuple
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static import now, thread_decorator


VOLATILITY_PATTERN_DB = f'{DB_PATH}/volatility_pattern.db'
window_queue = None


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


class AnalyzerVolatilityPattern:
    """메인 변동성 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, min_samples: int = 20):
        """
        초기화
        :param market_gubun: 마켓 구분 번호
        :param market_info: 마켓 정보 딕셔너리
        :param min_samples: 최소 샘플 수 (기본값 20)
        """
        self.backtest_db_path    = market_info['백테디비'][0]
        self.factor_list         = market_info['팩터목록'][0]
        self.strategy_gubun      = market_info['전략구분']
        self.volatility_database = VolatilityPatternDatabase(self.strategy_gubun)
        analysis_period, rate_threshold, num_levels = self.volatility_database.load_volatility_setting(market_gubun)
        self.analysis_period     = analysis_period
        self.rate_threshold      = rate_threshold
        self.num_levels          = num_levels
        self.min_samples         = min_samples
        self.volatility_realtime = \
            VolatilityPatternRealtime(self.factor_list, self.strategy_gubun, analysis_period, num_levels)

    def analyze_current_volatility(self, code: str, realtime_data: np.ndarray) -> Dict[str, float]:
        """
        실시간 변동성 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
        :return: 변동성 분석 결과
        """
        return self.volatility_realtime.analyze_current_volatility(code, realtime_data)

    def train_all_codes(self, windowQ):
        """전체 종목 패턴 학습 수행 (종목 기반 멀티프로세싱)"""
        code_list     = self.get_code_list()
        num_processes = cpu_count()
        code_chunks   = self._split_codes(code_list, num_processes)

        actual_processes = min(num_processes, len(code_chunks))
        with Pool(processes=actual_processes, initializer=init_worker, initargs=(windowQ,)) as pool:
            args = [(i, chunk, self.backtest_db_path, self.factor_list, self.analysis_period,
                     self.rate_threshold, self.num_levels, self.min_samples)
                    for i, chunk in enumerate(code_chunks)]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            for code, (volatility_scores, level_boundaries) in chunk_results.items():
                self.volatility_database.save_volatility_scores(code, volatility_scores, level_boundaries)
                total_processed += 1
            windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i + 1}/{actual_processes}]"))

        windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
        windowQ.put((UI_NUM['학습로그'], f"{VOLATILITY_PATTERN_DB} -> {self.volatility_database.table_name}"))
        windowQ.put((UI_NUM['학습로그'], f"변동성분석 학습 완료 [{total_processed}]"))

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
                          analysis_period: int, num_levels: int, min_samples: int) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db_path: 백테디비 경로
        market_info: 마켓 정보 딕셔너리
        analysis_period: 분석 기간 분
        num_levels: 변동성 레벨 수
        volatility_method: 변동성 계산 방법
        min_samples: 최소 샘플 수
        return: 종목별 변동성 점수 딕셔너리 {code: volatility_scores}
        """
        global window_queue
        volatility_learning = \
            VolatilityPatternLearning(factor_list, analysis_period, num_levels, min_samples)
        all_volatility_scores = {}
        last = len(code_chunk)
        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)
                volatility_scores, level_boundaries = volatility_learning.train_volatility_patterns(historical_data)
                if volatility_scores:
                    all_volatility_scores[code] = (volatility_scores, level_boundaries)
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 변동성 패턴 학습 중 ... [{k + 1}/{last}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i}][{code}] 변동성 패턴 학습 실패 - {e}"))

        return all_volatility_scores


class VolatilityPatternLearning:
    """과거데이터 기반 변동성 패턴 학습 모듈"""
    def __init__(self, factor_list: list, analysis_period: int, num_levels: int, min_samples: int):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param analysis_period: 분석 기간 분 (기본값 30)
        :param num_levels: 변동성 레벨 수 (기본값 5)
        :param min_samples: 최소 샘플 수 (기본값 20)
        """
        self.idx_close       = factor_list.index('현재가')
        self.idx_high        = factor_list.index('분봉고가')
        self.idx_low         = factor_list.index('분봉저가')
        self.analysis_period = analysis_period
        self.num_levels      = num_levels
        self.min_samples     = min_samples

    def train_volatility_patterns(self, historical_data: np.ndarray) -> Tuple[Dict[int, Dict[str, float]], np.ndarray]:
        """
        종목별 과거데이터로 변동성 패턴 학습
        :param historical_data: 과거 1분봉 데이터 (2차원 numpy 어레이)
        :return: (변동성 레벨별 점수 딕셔너리, 레벨 경계 배열)
        """
        recent_data = historical_data[-10000:] if len(historical_data) > 10000 else historical_data
        close_price = recent_data[:, self.idx_close]
        high_price  = recent_data[:, self.idx_high]
        low_price   = recent_data[:, self.idx_low]

        volatility_data = self._calculate_volatility(close_price, high_price, low_price)
        volatility_levels, level_boundaries = self._classify_volatility_levels(volatility_data)

        level_scores = {}
        for level in range(self.num_levels):
            level_indices = np.where(volatility_levels == level)[0]

            if len(level_indices) >= self.min_samples:
                scores = []
                for idx in level_indices:
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
                    level_scores[level] = {
                        'avg_score': float(np.mean(scores)),
                        'max_score': float(np.max(scores)),
                        'min_score': float(np.min(scores)),
                        'std_score': float(np.std(scores)),
                        'sample_count': len(scores),
                        'confidence_score': confidence
                    }

        return level_scores, level_boundaries

    def _calculate_volatility(self, close_price: np.ndarray, high_price: np.ndarray,
                              low_price: np.ndarray) -> np.ndarray:
        """변동성 계산"""
        tr1 = high_price[1:] - low_price[1:]
        tr2 = np.abs(high_price[1:] - close_price[:-1])
        tr3 = np.abs(low_price[1:] - close_price[:-1])
        tr  = np.maximum(tr1, tr2, tr3)
        atr = np.zeros(len(close_price))
        for i in range(self.analysis_period, len(close_price)):
            atr[i] = np.mean(tr[i-self.analysis_period:i])
        return atr

    def _classify_volatility_levels(self, volatility_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """변동성 레벨 분류 및 경계 계산"""
        # 유효한 데이터만 사용
        valid_data = volatility_data[volatility_data > 0]

        if len(valid_data) < self.num_levels:
            return np.zeros(len(volatility_data), dtype=int), np.linspace(0, 1, self.num_levels + 1)

        # 백분위수 기반 레벨 경계 계산
        percentiles      = np.linspace(0, 100, self.num_levels + 1)
        level_boundaries = np.percentile(valid_data, percentiles)

        # 각 변동성 값에 레벨 할당
        levels = np.zeros(len(volatility_data), dtype=int)
        for i in range(len(volatility_data)):
            if volatility_data[i] > 0:
                for level in range(self.num_levels):
                    if level_boundaries[level] <= volatility_data[i] < level_boundaries[level + 1]:
                        levels[i] = level
                        break
                # 최대값 처리
                if volatility_data[i] >= level_boundaries[-1]:
                    levels[i] = self.num_levels - 1

        return levels, level_boundaries

    def _calculate_score(self, price_change_percent: float) -> float:
        """가격변화율을 기반으로 점수 계산"""
        score = (price_change_percent / 5.0) * 100
        return max(-100.0, min(100.0, score))

    def _calculate_confidence(self, sample_count: int, std_score: float) -> float:
        """신뢰도 계산"""
        sample_factor = min(sample_count / 100.0, 1.0)
        std_factor = max(1.0 - std_score / 50.0, 0.0)
        return (sample_factor + std_factor) / 2.0


class VolatilityPatternRealtime:
    """실시간 변동성 패턴 분석 모듈"""
    def __init__(self, factor_list: list, strategy_gubun: str, analysis_period: int, num_levels: int):
        """
        초기화
        :param factor_list: 팩터 리스트
        :param strategy_gubun: 전략 구분
        :param analysis_period: 분석 기간 분 (기본값 30)
        :param num_levels: 변동성 레벨 수 (기본값 5)
        """
        self.idx_close           = factor_list.index('현재가')
        self.idx_high            = factor_list.index('분봉고가')
        self.idx_low             = factor_list.index('분봉저가')
        self.analysis_period     = analysis_period
        self.num_levels          = num_levels
        self.volatility_database = VolatilityPatternDatabase(strategy_gubun)
        self.volatility_scores   = {}
        self.level_boundaries    = {}
        self._load_volatility_scores()

    def _load_volatility_scores(self):
        """데이터베이스에서 모든 종목의 변동성 점수 로드"""
        all_codes = self.volatility_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volatility_scores[code], self.level_boundaries[code] = \
                    self.volatility_database.get_all_volatility_scores(code)

    def analyze_current_volatility(self, code: str, realtime_data: np.ndarray) -> Dict[str, float]:
        """
        현재 변동성 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터
        :return: 변동성 분석 결과
        """
        volatility_level = 0
        volatility_value = 0.0
        volatility_score = 0.0
        confidence       = 0.0

        if len(realtime_data) >= self.analysis_period:
            close_price = realtime_data[:, self.idx_close]
            high_price  = realtime_data[:, self.idx_high]
            low_price   = realtime_data[:, self.idx_low]

            volatility_data  = self._calculate_volatility(close_price, high_price, low_price)
            volatility_value = volatility_data[-1]
            volatility_level = self._estimate_level(code, volatility_value)

            if code in self.volatility_scores and volatility_level in self.volatility_scores[code]:
                score_data       = self.volatility_scores[code][volatility_level]
                volatility_score = score_data['avg_score']
                confidence       = score_data['confidence_score']

        return {
            'volatility_level': volatility_level,
            'volatility_value': volatility_value,
            'score': volatility_score,
            'confidence': confidence
        }

    def _calculate_volatility(self, close_price: np.ndarray, 
                              high_price: np.ndarray, low_price: np.ndarray) -> np.ndarray:
        """변동성 계산"""
        tr1 = high_price[1:] - low_price[1:]
        tr2 = np.abs(high_price[1:] - close_price[:-1])
        tr3 = np.abs(low_price[1:] - close_price[:-1])
        tr  = np.maximum(tr1, tr2, tr3)
        atr = np.zeros(len(close_price))
        for i in range(self.analysis_period, len(close_price)):
            atr[i] = np.mean(tr[i-self.analysis_period:i])
        return atr

    def _estimate_level(self, code: str, volatility_value: float) -> int:
        """학습된 레벨 경계를 사용하여 변동성 레벨 추정"""
        if code in self.level_boundaries:
            boundaries = self.level_boundaries[code]
            for level in range(len(boundaries) - 1):
                if boundaries[level] <= volatility_value < boundaries[level + 1]:
                    return level
            if volatility_value >= boundaries[-1]:
                return len(boundaries) - 2
        return 0


class VolatilityPatternDatabase:
    """변동성 패턴 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str):
        self.table_name = f'{strategy_gubun}_volatility_pattern'
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS volatility_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    num_levels INTEGER NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    volatility_level INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    last_update TEXT NOT NULL,
                    level_boundaries TEXT NOT NULL,
                    PRIMARY KEY (code, volatility_level)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        :return: 종목코드 리스트
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_all_volatility_scores(self, code: str) -> Tuple[Dict[int, Dict[str, float]], np.ndarray]:
        """
        종목의 전체 변동성 점수 조회
        code: 종목코드
        return: (변동성 레벨별 점수 딕셔너리, 레벨 경계 배열)
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, avg_score, max_score, min_score, std_score, sample_count,
                confidence_score, level_boundaries
                FROM {self.table_name}
                WHERE code = ?
            ''', (code,))
            results = cursor.fetchall()

            volatility_scores = {}
            level_boundaries = None
            for result in results:
                volatility_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
                level_boundaries = np.array(list(map(float, result[7].split(','))))

            if level_boundaries is None:
                level_boundaries = np.linspace(0, 1, 6)

            return volatility_scores, level_boundaries

    def save_volatility_scores(self, code: str, volatility_scores: Dict[int, Dict[str, float]],
                               level_boundaries: np.ndarray):
        """
        종목별 변동성 점수 저장
        code: 종목코드
        volatility_scores: 변동성 레벨별 점수 딕셔너리
        level_boundaries: 레벨 경계 배열
        """
        current_date = now().strftime('%Y-%m-%d')
        boundaries_str = ','.join(map(str, level_boundaries))

        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            for volatility_level, scores in volatility_scores.items():
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {self.table_name} 
                    (code, volatility_level, avg_score, max_score, min_score, std_score, sample_count,
                    confidence_score, level_boundaries, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    volatility_level,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    boundaries_str,
                    current_date
                ))
            conn.commit()

    def load_volatility_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (analysis_period, num_levels, volatility_method) 튜플, 데이터가 없으면 ('std', 20, 10) 반환
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, num_levels, volatility_method FROM volatility_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if result:
                return result
            return 'std', 5, 20

    def save_volatility_setting(self, market: int, analysis_period: int, num_levels: int, volatility_method: str):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        num_levels: 변동성 레벨 수
        volatility_method: 변동성 계산 방법
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO volatility_setting '
                '(market, analysis_period, num_levels, volatility_method) VALUES (?, ?, ?, ?)',
                (market, analysis_period, num_levels, volatility_method)
            )
            conn.commit()


def volatility_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    volatility_database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, num_levels = volatility_database.load_volatility_setting(ui.market_gubun)
    ui.vlp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vlp_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vlp_comboBoxxx_03.setCurrentText(str(num_levels))


def volatility_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period     = int(ui.vlp_comboBoxxx_01.currentText())
    rate_threshold      = int(ui.vlp_comboBoxxx_02.currentText())
    num_levels          = int(ui.vlp_comboBoxxx_03.currentText())
    volatility_database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    volatility_database.save_volatility_setting(ui.market_gubun, analysis_period, rate_threshold, num_levels)
    QMessageBox.information(ui.dialog_volatility, '저장완료', random.choice(famous_saying))


def volatility_train(ui):
    """변동성 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_volatility, '오류 알림', '현재 변동성 패턴 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vlp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vlp_comboBoxxx_02.currentText())
    _num_levels      = int(ui.vlp_comboBoxxx_03.currentText())
    volatility_database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, num_levels = volatility_database.load_volatility_setting(ui.market_gubun)
    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _num_levels != num_levels:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _volatility_train(ui)


@thread_decorator
def _volatility_train(ui):
    """스레드로 변동성 패턴 학습을 시작한다."""
    ui.learn_running = True
    vp_analyzer = AnalyzerVolatilityPattern(ui.market_gubun, ui.market_info)
    vp_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
