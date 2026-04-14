"""
전략 생성기
자연어를 전략 코드로 변환하는 메인 클래스
"""

import os
from datetime import datetime
from typing import Optional, List
from .openai_client import OpenAIClient
from .syntax_validator import SyntaxValidator


class StrategyGenerator:
    """자연어 전략 생성 메인 클래스"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", 
                 strategy_vars_path: Optional[str] = None):
        """
        전략 생성기 초기화
        
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델 (기본값: gpt-4)
            strategy_vars_path: strategy.txt 파일 경로 (None인 경우 기본 경로 사용)
        """
        self.openai_client = OpenAIClient(api_key, model)
        
        if strategy_vars_path is None:
            # 기본 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            strategy_vars_path = os.path.join(
                os.path.dirname(current_dir), 'strategy.txt'
            )
        
        self.validator = SyntaxValidator(strategy_vars_path)
        self.buy_templates = []
        self.sell_templates = []
        
        # 템플릿 로드
        self.load_templates()
    
    def load_templates(self):
        """템플릿 파일 로드"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(current_dir, 'templates')
        
        # 매수전략 템플릿 로드
        buy_template_path = os.path.join(templates_dir, 'buy_templates.txt')
        if os.path.exists(buy_template_path):
            with open(buy_template_path, 'r', encoding='utf-8') as f:
                self.buy_templates = self._parse_templates(f.read())
        
        # 매도전략 템플릿 로드
        sell_template_path = os.path.join(templates_dir, 'sell_templates.txt')
        if os.path.exists(sell_template_path):
            with open(sell_template_path, 'r', encoding='utf-8') as f:
                self.sell_templates = self._parse_templates(f.read())
    
    def _parse_templates(self, content: str) -> List[dict]:
        """
        템플릿 파일 내용 파싱
        
        Args:
            content: 템플릿 파일 내용
        
        Returns:
            템플릿 딕셔너리 리스트
        """
        templates = []
        lines = content.split('\n')
        
        current_template = None
        code_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 템플릿 시작
            if line.startswith('# 템플릿'):
                if current_template and code_lines:
                    current_template['code'] = '\n'.join(code_lines)
                    templates.append(current_template)
                
                current_template = {'name': line, 'description': '', 'example': ''}
                code_lines = []
            
            # 설명
            elif line.startswith('# 설명:'):
                if current_template:
                    current_template['description'] = line.replace('# 설명:', '').strip()
            
            # 자연어 예시
            elif line.startswith('# 자연어 예시:'):
                if current_template:
                    current_template['example'] = line.replace('# 자연어 예시:', '').strip()
            
            # 코드 (주석이 아닌 줄)
            elif line and not line.startswith('#') and not line.startswith('='):
                code_lines.append(line)
        
        # 마지막 템플릿 추가
        if current_template and code_lines:
            current_template['code'] = '\n'.join(code_lines)
            templates.append(current_template)
        
        return templates
    
    def generate_buy_strategy(self, natural_language: str) -> tuple[bool, str, str]:
        """
        매수전략 생성
        
        Args:
            natural_language: 사용자 입력 (예: "등락율이 3% 이상이고 체결강도가 100 이상일 때 매수")
        
        Returns:
            (성공여부, 생성된 코드, 에러메시지)
        """
        try:
            # OpenAI API로 코드 생성
            code = self.openai_client.generate_strategy_code(
                natural_language, 
                strategy_type="buy"
            )
            
            # 코드 클린업 (코드 블록 제거 등)
            code = self._clean_code(code)
            
            # 구문 검사
            syntax_valid, syntax_error = self.validator.validate_code(code)
            if not syntax_valid:
                return False, "", f"구문 오류: {syntax_error}"
            
            # 변수 검사
            var_valid, invalid_vars = self.validator.validate_variables(code)
            if not var_valid:
                return False, "", f"미허용 변수 사용: {', '.join(invalid_vars)}"
            
            return True, code, ""
            
        except Exception as e:
            return False, "", f"전략 생성 중 오류 발생: {str(e)}"
    
    def generate_sell_strategy(self, natural_language: str) -> tuple[bool, str, str]:
        """
        매도전략 생성
        
        Args:
            natural_language: 사용자 입력 (예: "수익률이 3% 이상이거나 -2% 이하일 때 매도")
        
        Returns:
            (성공여부, 생성된 코드, 에러메시지)
        """
        try:
            # OpenAI API로 코드 생성
            code = self.openai_client.generate_strategy_code(
                natural_language, 
                strategy_type="sell"
            )
            
            # 코드 클린업
            code = self._clean_code(code)
            
            # 구문 검사
            syntax_valid, syntax_error = self.validator.validate_code(code)
            if not syntax_valid:
                return False, "", f"구문 오류: {syntax_error}"
            
            # 변수 검사
            var_valid, invalid_vars = self.validator.validate_variables(code)
            if not var_valid:
                return False, "", f"미허용 변수 사용: {', '.join(invalid_vars)}"
            
            return True, code, ""
            
        except Exception as e:
            return False, "", f"전략 생성 중 오류 발생: {str(e)}"
    
    def _clean_code(self, code: str) -> str:
        """
        코드 클린업 (코드 블록 제거 등)
        
        Args:
            code: 클린업할 코드
        
        Returns:
            클린업된 코드
        """
        # 코드 블록 제거 (```python, ``` 등)
        lines = code.split('\n')
        cleaned_lines = []
        
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if not in_code_block:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def save_strategy(self, strategy_code: str, strategy_name: str, 
                      strategy_type: str) -> tuple[bool, str]:
        """
        전략을 ai_agent/strategy 폴더에 저장
        
        Args:
            strategy_code: 저장할 전략 코드
            strategy_name: 전략 이름
            strategy_type: "buy" 또는 "sell"
        
        Returns:
            (성공여부, 저장된 파일 경로 또는 에러메시지)
        """
        try:
            # 저장 디렉토리 경로
            current_dir = os.path.dirname(os.path.abspath(__file__))
            strategy_dir = os.path.join(os.path.dirname(current_dir), 'strategy')
            
            # 디렉토리 생성
            os.makedirs(strategy_dir, exist_ok=True)
            
            # 파일명 생성: 한글전략명_생성일자및시간.txt
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            type_prefix = "매수전략" if strategy_type == "buy" else "매도전략"
            filename = f"{type_prefix}_{strategy_name}_{timestamp}.txt"
            filepath = os.path.join(strategy_dir, filename)
            
            # 파일 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {type_prefix}: {strategy_name}\n")
                f.write(f"# 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 자연어 설명: {strategy_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(strategy_code)
            
            return True, filepath
            
        except Exception as e:
            return False, f"파일 저장 중 오류 발생: {str(e)}"
    
    def get_buy_templates(self) -> List[dict]:
        """매수전략 템플릿 목록 반환"""
        return self.buy_templates
    
    def get_sell_templates(self) -> List[dict]:
        """매도전략 템플릿 목록 반환"""
        return self.sell_templates
    
    def display_templates(self, strategy_type: str):
        """
        템플릿 표시
        
        Args:
            strategy_type: "buy" 또는 "sell"
        """
        templates = self.buy_templates if strategy_type == "buy" else self.sell_templates
        
        print(f"\n{'='*80}")
        print(f"{strategy_type.upper()}전략 템플릿 목록")
        print(f"{'='*80}\n")
        
        for i, template in enumerate(templates, 1):
            print(f"템플릿 {i}: {template['name']}")
            print(f"설명: {template['description']}")
            print(f"자연어 예시: {template['example']}")
            print(f"코드:")
            print(template['code'])
            print(f"{'-'*80}\n")
