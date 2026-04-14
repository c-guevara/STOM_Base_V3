"""
CLI 인터페이스
자연어 전략생성 모듈의 커맨드 라인 인터페이스
"""

import os
import sys
from typing import Optional
from .strategy_generator import StrategyGenerator


def get_api_key() -> Optional[str]:
    """
    API 키 가져오기
    환경 변수 또는 사용자 입력에서 API 키를 가져옴
    
    Returns:
        API 키 문자열 또는 None
    """
    # 환경 변수 확인
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        return api_key
    
    # 사용자 입력
    print("OpenAI API 키를 입력해주세요.")
    print("(환경 변수 OPENAI_API_KEY를 설정하면 매번 입력하지 않아도 됩니다)")
    api_key = input("API Key: ").strip()
    
    if api_key:
        return api_key
    
    return None


def display_main_menu():
    """메인 메뉴 표시"""
    print("\n" + "="*80)
    print("자연어 전략생성 모듈")
    print("="*80)
    print("1. 매수전략 생성")
    print("2. 매도전략 생성")
    print("3. 매수전략 템플릿 보기")
    print("4. 매도전략 템플릿 보기")
    print("5. 종료")
    print("="*80)


def generate_buy_strategy(generator: StrategyGenerator):
    """매수전략 생성"""
    print("\n--- 매수전략 생성 ---")
    print("생성할 매수전략을 자연어로 설명해주세요.")
    print("예: 등락율이 3% 이상이고 체결강도가 100 이상일 때 매수")
    
    natural_language = input("\n전략 설명: ").strip()
    if not natural_language:
        print("전략 설명을 입력해주세요.")
        return
    
    strategy_name = input("전략 이름 (저장용): ").strip()
    if not strategy_name:
        strategy_name = natural_language[:20]  # 설명의 앞부분을 이름으로 사용
    
    print("\n전략 생성 중...")
    
    # 전략 생성
    success, code, error = generator.generate_buy_strategy(natural_language)
    
    if success:
        print("\n성공적으로 전략이 생성되었습니다.")
        print("\n생성된 코드:")
        print("-" * 80)
        print(code)
        print("-" * 80)
        
        # 저장 여부 확인
        save = input("\n이 전략을 저장하시겠습니까? (y/n): ").strip().lower()
        if save == 'y':
            save_success, result = generator.save_strategy(code, strategy_name, "buy")
            if save_success:
                print(f"전략이 저장되었습니다: {result}")
            else:
                print(f"저장 실패: {result}")
    else:
        print(f"\n전략 생성 실패: {error}")
        print("\n팁: 설명을 더 구체적으로 작성해 보세요.")


def generate_sell_strategy(generator: StrategyGenerator):
    """매도전략 생성"""
    print("\n--- 매도전략 생성 ---")
    print("생성할 매도전략을 자연어로 설명해주세요.")
    print("예: 수익률이 3% 이상이거나 -2% 이하일 때 매도")
    
    natural_language = input("\n전략 설명: ").strip()
    if not natural_language:
        print("전략 설명을 입력해주세요.")
        return
    
    strategy_name = input("전략 이름 (저장용): ").strip()
    if not strategy_name:
        strategy_name = natural_language[:20]
    
    print("\n전략 생성 중...")
    
    # 전략 생성
    success, code, error = generator.generate_sell_strategy(natural_language)
    
    if success:
        print("\n성공적으로 전략이 생성되었습니다.")
        print("\n생성된 코드:")
        print("-" * 80)
        print(code)
        print("-" * 80)
        
        # 저장 여부 확인
        save = input("\n이 전략을 저장하시겠습니까? (y/n): ").strip().lower()
        if save == 'y':
            save_success, result = generator.save_strategy(code, strategy_name, "sell")
            if save_success:
                print(f"전략이 저장되었습니다: {result}")
            else:
                print(f"저장 실패: {result}")
    else:
        print(f"\n전략 생성 실패: {error}")
        print("\n팁: 설명을 더 구체적으로 작성해 보세요.")


def display_buy_templates(generator: StrategyGenerator):
    """매수전략 템플릿 표시"""
    generator.display_templates("buy")


def display_sell_templates(generator: StrategyGenerator):
    """매도전략 템플릿 표시"""
    generator.display_templates("sell")


def main():
    """CLI 메인 함수"""
    print("\n자연어 전략생성 모듈에 오신 것을 환영합니다!")
    
    # API 키 가져오기
    api_key = get_api_key()
    if not api_key:
        print("API 키가 필요합니다.")
        sys.exit(1)
    
    # 전략 생성기 초기화
    try:
        generator = StrategyGenerator(api_key)
        print("전략 생성기가 초기화되었습니다.")
    except Exception as e:
        print(f"초기화 실패: {str(e)}")
        sys.exit(1)
    
    # 메인 루프
    while True:
        display_main_menu()
        choice = input("선택: ").strip()
        
        if choice == "1":
            generate_buy_strategy(generator)
        elif choice == "2":
            generate_sell_strategy(generator)
        elif choice == "3":
            display_buy_templates(generator)
        elif choice == "4":
            display_sell_templates(generator)
        elif choice == "5":
            print("\n프로그램을 종료합니다.")
            break
        else:
            print("\n잘못된 선택입니다. 다시 선택해주세요.")
        
        # 계속 여부 확인
        if choice != "5":
            input("\n계속하려면 Enter를 누르세요...")


if __name__ == "__main__":
    main()
