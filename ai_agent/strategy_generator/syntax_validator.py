"""
구문 검사기
생성된 전략 코드의 파이썬 구문을 검사하고 변수 유효성을 확인
"""

import ast
import re
from typing import Tuple, List, Set


class SyntaxValidator:
    """파이썬 코드 구문 검사 및 변수 유효성 검사"""
    
    def __init__(self, strategy_vars_path: str):
        """
        구문 검사기 초기화
        
        Args:
            strategy_vars_path: strategy.txt 파일 경로
        """
        self.allowed_variables = self._load_allowed_variables(strategy_vars_path)
    
    def _load_allowed_variables(self, path: str) -> Set[str]:
        """
        strategy.txt에서 허용된 변수 목록 로드
        
        Args:
            path: strategy.txt 파일 경로
        
        Returns:
            허용된 변수 이름 집합
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 변수명 추출 (한글 변수명)
            variables = set()
            
            # 기본 변수들 (쉼표로 구분)
            basic_var_pattern = r'현재가|시가|고가|저가|등락율|당일거래대금|체결강도|초당매수수량|초당매도수량|'
            basic_var_pattern += r'초당거래대금|고저평균대비등락율|저가대비고가등락율|초당매수금액|초당매도금액|'
            basic_var_pattern += r'당일매수금액|당일매도금액|최고매수금액|최고매도금액|최고매수가격|최고매도가격|'
            basic_var_pattern += r'매도호가[1-5]|매도잔량[1-5]|매수호가[1-5]|매수잔량[1-5]|'
            basic_var_pattern += r'매도총잔량|매수총잔량|매도수5호가잔량합|관심종목|'
            basic_var_pattern += r'분당매수수량|분당매도수량|분봉시가|분봉고가|분봉저가|분당거래대금|'
            basic_var_pattern += r'분당매수금액|분당매도금액|분당거래대금평균|'
            basic_var_pattern += r'호가단위|데이터길이|시분초|종목명|종목코드|매수|매도|'
            basic_var_pattern += r'시가총액|VI해제시간|VI가격|VI호가단위|'
            basic_var_pattern += r'수익금|수익률|매수가|보유수량|보유시간|분할매수횟수|분할매도횟수|'
            basic_var_pattern += r'최고수익률|최저수익률|'
            basic_var_pattern += r'AD|ADOSC|ADXR|APO|AROOND|AROONU|ATR|BBU|BBM|BBL|CCI|DIM|DIP|'
            basic_var_pattern += r'MACD|MACDS|MACDH|MFI|MOM|OBV|PPO|ROC|RSI|SAR|'
            basic_var_pattern += r'STOCHSK|STOCHSD|STOCHFK|STOCHFD|WILLR'
            
            # 기본 변수 추가
            for var in re.findall(basic_var_pattern, content):
                variables.add(var)
            
            # 함수들
            func_pattern = r'이동평균|최고현재가|최저현재가|초당거래대금평균|체결강도평균|'
            func_pattern += r'최고체결강도|최저체결강도|누적초당매수수량|누적초당매도수량|'
            func_pattern += r'최고초당매수수량|최고초당매도수량|당일거래대금각도|등락율각도|'
            func_pattern += r'분당거래대금평균|누적분당매수수량|누적분당매도수량|'
            func_pattern += r'최고분당매수수량|최고분당매도수량|'
            func_pattern += r'이평지지|이평돌파|이평이탈|시가지지|시가돌파|시가이탈|'
            func_pattern += r'변동성|변동성급증|변동성급감|연속상승|가격급등|거래대금급증|'
            func_pattern += r'매수수량급증|매도수량급증|연속하락|가격급락|거래대금급감|'
            func_pattern += r'매수수량급감|매도수량급감|횡보감지|횡보후가격급등|횡보후연속상승|'
            func_pattern += r'횡보후가격급락|횡보후연속하락|호가상승압력|호가하락압력|'
            func_pattern += r'체결강도급등|체결강도급락|호가갭발생|횡보상태장기보유|'
            func_pattern += r'변동성급증_역추세매도|장기보유종목_동적익절청산|'
            func_pattern += r'거래대금비율기반_동적청산|호가압력기반_동적청산|'
            func_pattern += r'이평기반_동적청산|변동성기반_동적청산|변동성급증기반_동적청산|'
            func_pattern += r'저점기준등락율각도|고점기준등락율각도|'
            func_pattern += r'구간저가대비현재가등락율|구간고가대비현재가등락율|'
            func_pattern += r'거래대금평균대비비율|체결강도평균대비비율|구간호가총잔량비율|'
            func_pattern += r'매수수량변동성|매도수량변동성|고가미갱신지속틱수|저가미갱신지속틱수'
            
            for func in re.findall(func_pattern, content):
                variables.add(func)
            
            # self, Buy, Sell 추가
            variables.add('self')
            variables.add('Buy')
            variables.add('Sell')
            
            return variables
            
        except Exception as e:
            print(f"경고: 변수 목록 로드 실패 - {str(e)}")
            return set()
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        파이썬 코드 구문 검사
        
        Args:
            code: 검사할 파이썬 코드
        
        Returns:
            (유효성, 에러메시지)
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            error_msg = f"구문 오류 (라인 {e.lineno}): {e.msg}"
            return False, error_msg
        except Exception as e:
            return False, f"검사 중 오류 발생: {str(e)}"
    
    def validate_variables(self, code: str) -> Tuple[bool, List[str]]:
        """
        사용된 변수가 허용된 변수인지 검사
        
        Args:
            code: 검사할 파이썬 코드
        
        Returns:
            (유효성, 미허용 변수 목록)
        """
        # 코드에서 사용된 변수 추출
        used_vars = set()
        
        # 식별자 추출 (한글 포함)
        pattern = r'[가-힣a-zA-Z_][가-힣a-zA-Z0-9_]*'
        for match in re.finditer(pattern, code):
            var = match.group()
            # Python 키워드 제외
            if var not in ['if', 'elif', 'else', 'not', 'and', 'or', 'True', 'False', 'return', 'def', 'class']:
                used_vars.add(var)
        
        # 미허용 변수 찾기
        invalid_vars = []
        for var in used_vars:
            # 변수가 허용된 변수 집합에 없거나, 허용된 변수의 접두사가 아닌 경우
            is_valid = False
            for allowed in self.allowed_variables:
                if var == allowed or var.startswith(allowed + '(') or var.startswith(allowed + 'N('):
                    is_valid = True
                    break
            
            # 숫자로 끝나는 변수들 (예: 매도호가1, 매도잔량1 등) 처리
            if not is_valid:
                for allowed in self.allowed_variables:
                    if allowed.endswith('[1-5]') or allowed.endswith('~5'):
                        base = allowed.replace('[1-5]', '').replace('~5', '')
                        if var.startswith(base):
                            is_valid = True
                            break
            
            if not is_valid and var not in ['self', 'Buy', 'Sell']:
                invalid_vars.append(var)
        
        if invalid_vars:
            return False, invalid_vars
        return True, []
    
    def full_validation(self, code: str) -> Tuple[bool, str]:
        """
        구문 검사와 변수 검사를 모두 수행
        
        Args:
            code: 검사할 파이썬 코드
        
        Returns:
            (유효성, 전체 에러메시지)
        """
        # 구문 검사
        syntax_valid, syntax_error = self.validate_code(code)
        if not syntax_valid:
            return False, syntax_error
        
        # 변수 검사
        var_valid, invalid_vars = self.validate_variables(code)
        if not var_valid:
            error_msg = f"미허용 변수 사용: {', '.join(invalid_vars)}"
            return False, error_msg
        
        return True, "검사 통과"
