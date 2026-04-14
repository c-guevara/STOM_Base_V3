"""
OpenAI API 클라이언트
자연어를 전략 코드로 변환하기 위한 OpenAI GPT API 연동
"""

import openai
from typing import Optional


class OpenAIClient:
    """OpenAI API를 사용하여 자연어를 전략 코드로 변환하는 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        OpenAI API 클라이언트 초기화
        
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델 (기본값: gpt-4)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate_strategy_code(self, natural_language: str, 
                               strategy_type: str,
                               system_prompt: Optional[str] = None) -> str:
        """
        자연어를 전략 코드로 변환
        
        Args:
            natural_language: 사용자 입력 (예: "등락율이 3% 이상이고 체결강도가 100 이상일 때 매수")
            strategy_type: "buy" 또는 "sell"
            system_prompt: 시스템 프롬프트 (None인 경우 기본 프롬프트 사용)
        
        Returns:
            파이썬 전략 코드 문자열
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        user_prompt = self._build_user_prompt(natural_language, strategy_type)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            code = response.choices[0].message.content.strip()
            return code
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 중 오류 발생: {str(e)}")
    
    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트 반환"""
        return """
당신은 트레이딩 전략 코드 생성 전문가입니다.
사용자의 자연어 설명을 파이썬 코드로 변환하세요.

사용 가능한 변수:
[기본 변수들]
현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 
초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 
당일매수금액, 당일매도금액, 최고매수금액, 최고매도금액, 최고매수가격, 최고매도가격, 
매도호가1~5, 매도잔량1~5, 매수호가1~5, 매수잔량1~5, 매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목

[구간연산 변수들 - 괄호 안에 '변수명(구간틱수, 이전틱수)' 형태로 사용]
이동평균, 최고현재가, 최저현재가, 초당거래대금평균, 체결강도평균, 최고체결강도, 최저체결강도, 
누적초당매수수량, 누적초당매도수량, 최고초당매수수량, 최고초당매도수량, 당일거래대금각도, 등락율각도

[복합 함수들]
이평지지(60, 30, 0.5, 10), 이평돌파(60, 1), 이평이탈(60, 1), 시가지지(30, 0.5, 10), 
시가돌파(30, 1), 시가이탈(30, 1), 변동성(30), 변동성급증(30, 2), 변동성급감(30, 0.5), 
연속상승(3), 가격급등(10, 1), 거래대금급증(30, 3), 매수수량급증(30, 3), 매도수량급증(30, 3),
연속하락(3), 가격급락(10, 1), 거래대금급감(30, 0.5), 매수수량급감(30, 0.5), 매도수량급감(30, 0.5),
횡보후가격급등(30, 0.5, 30, 1), 횡보후연속상승(30, 0.5, 3), 횡보후가격급락(30, 0.5, 30, 1), 
횡보후연속하락(30, 0.5, 3), 호가상승압력(30, 0.7), 호가하락압력(30, 0.3), 체결강도급등(30, 1.1), 
체결강도급락(30, 0.9), 기타 strategy.txt에 정의된 모든 변수와 함수

코드 형식:
- 매수전략: 매수 = True로 시작, 조건 불만족 시 매수 = False, 마지막에 self.Buy() 호출
- 매도전략: 매도 = False로 시작, 조건 만족 시 매도 = True, 마지막에 self.Sell() 호출
- 조건은 if not (조건): 매수 = False 또는 elif not (조건): 매수 = False 형태로 작성
- 최종적으로 if 매수: self.Buy() 또는 if 매도: self.Sell()로 마무리

주의사항:
- 코드 블록(```python 등) 없이 순수 파이썬 코드만 출력
- 주석은 최소화하고 핵심 로직만 작성
- 변수명은 strategy.txt에 정의된 이름 그대로 사용
- 조건문은 and/or 연산자를 적절히 사용
"""
    
    def _build_user_prompt(self, natural_language: str, strategy_type: str) -> str:
        """사용자 프롬프트 구성"""
        type_name = "매수전략" if strategy_type == "buy" else "매도전략"
        return f"""
전략 유형: {type_name}
사용자 설명: {natural_language}

위 설명을 바탕으로 전략 코드를 생성하세요.
코드 블록 없이 순수 파이썬 코드만 출력하세요.
"""
