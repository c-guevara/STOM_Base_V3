
import os
import talib
import sqlite3
import numpy as np
from typing import Dict, List
from multiprocessing import Pool
from utility.static_method.static import now


PATTERN_FUNCTIONS = [
    'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE', 'CDL3OUTSIDE',
    'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD',
    'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL', 'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER',
    'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI', 'CDLENGULFING', 'CDLEVENINGDOJISTAR',
    'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE', 'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN',
    'CDLHARAMI', 'CDLHARAMICROSS', 'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD',
    'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS', 'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING',
    'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU',
    'CDLMATCHINGLOW', 'CDLMATHOLD', 'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK',
    'CDLPIERCING', 'CDLRICKSHAWMAN', 'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR',
    'CDLSHORTLINE', 'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH', 'CDLTAKURI',
    'CDLTASUKIGAP', 'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS',
    'CDLXSIDEGAP3METHODS'
]


class AnalyzerPattern:
    """메인 패턴 분석 통합 클래스"""

    def __init__(self, market_info: dict, db_path: str = './_database/pattern_analysis.db'):
        """
        초기화
        :param market_info: 마켓 정보 딕셔너리 (self.market_info)
        :param db_path: 데이터베이스 파일 경로
        """
        self.market_info      = market_info
        self.db_path          = db_path
        self.strategy_type    = market_info['전략구분']
        self.backtest_db_path = market_info['백테디비'][0]
        self.pattern_database = PatternDatabase(self.strategy_type, db_path)
        self.pattern_learning = PatternLearning(market_info, db_path)
        self.pattern_realtime = PatternRealtime(market_info, db_path)

    def analyze_patterns(self, code: str, realtime_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        실시간 패턴 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
        :return: 탐지된 패턴과 학습된 점수
        """
        return self.pattern_realtime.analyze_patterns(code, realtime_data)

    def get_all_pattern_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """
        종목의 전체 패턴 점수 조회
        :param code: 종목코드
        :return: 패턴별 점수 딕셔너리
        """
        return self.pattern_database.get_all_pattern_scores(code)

    def delete_all_pattern_scores(self, code: str):
        """
        종목의 전체 패턴 점수 삭제
        :param code: 종목코드
        """
        self.pattern_database.delete_all_pattern_scores(code)

    def train_all_codes(self, code_list: List[str] = None):
        """
        전체 종목 패턴 학습 수행
        :param code_list: 종목코드 리스트 (None이면 전체 종목)
        """
        if code_list is None:
            code_list = self.get_code_list()

        total = len(code_list)
        for i, code in enumerate(code_list):
            try:
                historical_data = self.load_data_for_code(code)
                self.pattern_learning.train_patterns(code, historical_data)
                print(f"[{i+1}/{total}] {code} 패턴 학습 완료")
            except Exception as e:
                print(f"[{i+1}/{total}] {code} 패턴 학습 실패: {e}")

    def get_code_list(self) -> List[str]:
        """
        백테 디비에서 종목코드 목록 추출
        :return: 종목코드 리스트
        """
        with sqlite3.connect(self.backtest_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' in result[0]]
            return code_list

    def load_data_for_code(self, code: str) -> np.ndarray:
        """
        종목별 데이터 로딩
        :param code: 종목코드
        :return: 2차원 numpy 어레이
        """
        with sqlite3.connect(self.backtest_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM "{code}"')
            results = cursor.fetchall()
            data_array = np.array(results)
            return data_array


class PatternLearning:
    """과거데이터 기반 패턴 점수 학습 모듈"""

    def __init__(self, market_info: dict, db_path: str = './_database/pattern_analysis.db'):
        """
        초기화
        :param market_info: 마켓 정보 딕셔너리 (self.market_info)
        :param db_path: 데이터베이스 파일 경로
        """
        self.market_info      = market_info
        self.strategy_type    = market_info['전략구분']
        factor_list           = market_info['팩터목록'][0]
        self.idx_open         = factor_list.index('분봉시가')
        self.idx_high         = factor_list.index('분봉고가')
        self.idx_low          = factor_list.index('분봉저가')
        self.idx_close        = factor_list.index('현재가')
        self.num_processes    = 8
        self.pattern_database = PatternDatabase(self.strategy_type, db_path)

    def train_patterns(self, code: str, historical_data: np.ndarray):
        """
        종목별 과거데이터로 패턴 점수 학습 (멀티프로세싱)
        :param code: 종목코드
        :param historical_data: 과거 1분봉 데이터 (2차원 numpy 어레이)
                             칼럼순서는 self.market_info['팩터목록'][0]에 따름
        """
        open_price     = historical_data[:, self.idx_open]
        high_price     = historical_data[:, self.idx_high]
        low_price      = historical_data[:, self.idx_low]
        close_price    = historical_data[:, self.idx_close]
        datetime_data  = historical_data[:, 0]
        pattern_chunks = self._split_patterns(PATTERN_FUNCTIONS, self.num_processes)

        with Pool(processes=self.num_processes) as pool:
            args = [(chunk, open_price, high_price, low_price, close_price, datetime_data)
                    for chunk in pattern_chunks]
            results = pool.starmap(self._train_pattern_chunk, args)

        pattern_scores = {}
        for result in results:
            pattern_scores.update(result)

        self.pattern_database.save_pattern_scores(code, pattern_scores)

    def _split_patterns(self, pattern_list: List[str], num_chunks: int) -> List[List[str]]:
        """패턴 목록을 8분할"""
        chunk_size = len(pattern_list) // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(pattern_list)
            chunks.append(pattern_list[start:end])
        return chunks

    def _train_pattern_chunk(self, pattern_chunk: List[str], open_price: np.ndarray,
                             high_price: np.ndarray, low_price: np.ndarray,
                             close_price: np.ndarray, datetime_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """패턴 청크별 학습 (프로세스 내에서 실행)"""
        pattern_scores = {}

        for pattern_name in pattern_chunk:
            pattern_func      = getattr(talib, pattern_name)
            pattern_result    = pattern_func(open_price, high_price, low_price, close_price)
            detection_indices = np.where(pattern_result != 0)[0]

            scores = []
            for idx in detection_indices:
                if idx + 30 < len(close_price):
                    entry_date = int(datetime_data[idx] // 10000)
                    exit_date = int(datetime_data[idx + 30] // 10000)
                    if entry_date == exit_date:
                        entry_price = close_price[idx]
                        exit_max_price = close_price[idx:idx + 30].max()
                        exit_min_price = close_price[idx:idx + 30].min()
                        if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                            exit_price = exit_max_price
                        else:
                            exit_price = exit_min_price

                        price_change = (exit_price - entry_price) / entry_price * 100
                        score = self._calculate_score(price_change)
                        scores.append(score)

            if len(scores) >= 10:
                pattern_scores[pattern_name] = {
                    'avg_score': float(np.mean(scores)),
                    'max_score': float(np.max(scores)),
                    'min_score': float(np.min(scores)),
                    'std_score': float(np.std(scores)),
                    'sample_count': len(scores)
                }

        return pattern_scores

    def _calculate_score(self, price_change_percent: float) -> float:
        """가격변화율을 기반으로 점수 계산"""
        score = (price_change_percent / 10.0) * 100
        return max(-100.0, min(100.0, score))


class PatternRealtime:
    """실시간 패턴인식 및 학습된 점수 반환 모듈"""

    def __init__(self, market_info: dict, db_path: str = './_database/pattern_analysis.db'):
        """
        초기화
        :param market_info: 마켓 정보 딕셔너리 (self.market_info)
        :param db_path: 데이터베이스 파일 경로
        """
        self.market_info      = market_info
        self.strategy_type    = market_info['전략구분']
        factor_list           = market_info['팩터목록'][0]
        self.idx_open         = factor_list.index('분봉시가')
        self.idx_high         = factor_list.index('분봉고가')
        self.idx_low          = factor_list.index('분봉저가')
        self.idx_close        = factor_list.index('현재가')
        self.pattern_database = PatternDatabase(self.strategy_type, db_path)
        self.pattern_scores   = {}
        self._load_all_pattern_scores()

    def _load_all_pattern_scores(self):
        """
        데이터베이스에서 모든 종목의 패턴 점수를 미리 로드
        """
        all_codes = self.pattern_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.pattern_scores[code] = self.pattern_database.get_all_pattern_scores(code)

    def analyze_patterns(self, code: str, realtime_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        실시간 데이터에서 패턴 탐지 및 학습된 점수 반환
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
                            칼럼순서는 self.market_info['팩터목록'][0]에 따름
        :return: 탐지된 패턴과 학습된 점수
        """
        pattern_score, reliability = 0, 0

        open_price  = realtime_data[:, self.idx_open]
        high_price  = realtime_data[:, self.idx_high]
        low_price   = realtime_data[:, self.idx_low]
        close_price = realtime_data[:, self.idx_close]

        for pattern_name in PATTERN_FUNCTIONS:
            pattern_func = getattr(talib, pattern_name)
            pattern_result = pattern_func(open_price, high_price, low_price, close_price)

            if pattern_result[-1] != 0:
                learned_score = self.pattern_scores.get(code, {}).get(pattern_name)
                if learned_score:
                    pattern_score = learned_score['avg_score']
                    reliability = self._calculate_reliability(learned_score)

        return pattern_score, reliability

    def _calculate_reliability(self, score_data: Dict[str, float]) -> float:
        """
        점수 데이터의 신뢰도 계산
        :param score_data: 학습된 점수 데이터
        :return: 신뢰도 (0 ~ 1)
        """
        sample_factor = min(score_data['sample_count'] / 100.0, 1.0)
        std_factor = max(1.0 - score_data['std_score'] / 50.0, 0.0)
        return (sample_factor + std_factor) / 2.0


class PatternDatabase:
    """패턴 점수 데이터베이스 관리 클래스"""

    def __init__(self, strategy_type: str, db_path: str = './_database/pattern_analysis.db'):
        """
        데이터베이스 초기화
        :param strategy_type: 전략구분 (stock, stock_etf, stock_etn, stock_usa, coin, future, future_nt, future_os, coin_future)
        :param db_path: 데이터베이스 파일 경로
        """
        self.strategy_type = strategy_type
        self.db_path       = db_path
        self.table_name    = f'{strategy_type}_pattern_score'
        self._ensure_db_directory()
        self._initialize_tables()

    def _ensure_db_directory(self):
        """데이터베이스 디렉토리 생성"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    last_update TEXT NOT NULL,
                    PRIMARY KEY (code, pattern_name)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        :return: 종목코드 리스트
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_all_pattern_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """
        종목의 전체 패턴 점수 조회
        :param code: 종목코드
        :return: 패턴별 점수 딕셔너리
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT pattern_name, avg_score, max_score, min_score, std_score, sample_count
                FROM {self.table_name}
                WHERE code = ?
            ''', (code,))
            results = cursor.fetchall()

            pattern_scores = {}
            for result in results:
                pattern_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5]
                }
            return pattern_scores

    def save_pattern_scores(self, code: str, pattern_scores: Dict[str, Dict[str, float]]):
        """
        종목별 패턴 점수 저장
        :param code: 종목코드
        :param pattern_scores: 패턴별 점수 딕셔너리
        """
        current_date = now().strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for pattern_name, scores in pattern_scores.items():
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {self.table_name} 
                    (code, pattern_name, avg_score, max_score, min_score, std_score, sample_count, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    pattern_name,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    current_date
                ))
            conn.commit()

    def delete_all_pattern_scores(self, code: str):
        """
        종목의 전체 패턴 점수 삭제
        :param code: 종목코드
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE code = ?', (code,))
            conn.commit()
