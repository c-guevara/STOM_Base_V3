
def get_ema_list(is_tick):
    """EMA 윈도우 리스트를 반환합니다.
    Args:
        is_tick: 틱 데이터 여부
    Returns:
        EMA 윈도우 리스트
    """
    return (60, 150, 300, 600, 1200) if is_tick else (5, 10, 20, 60, 120)


def get_profile_text(pr):
    """프로파일 텍스트를 가져옵니다.
    Args:
        pr: 프로파일 객체
    Returns:
        프로파일 텍스트
    """
    import io
    import pstats
    output = io.StringIO()
    stats = pstats.Stats(pr, stream=output)
    stats.sort_stats('cumulative')
    stats.print_stats(30)
    result = output.getvalue()
    output.close()
    return result


def get_logger(name):
    """로거를 생성합니다.
    Args:
        name: 로거 이름
    Returns:
        설정된 로거 인스턴스
    """
    import sys
    from loguru import logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <5}</level> | "
               f"<cyan>{name}</cyan> : "
               "<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    return logger


def threading_timer(sec, func, args=None):
    """스레드 타이머를 설정합니다.
    Args:
        sec: 초
        func: 실행할 함수
        args: 함수 인자
    """
    from threading import Timer
    if args is None:
        Timer(float(sec), func).start()
    else:
        Timer(float(sec), func, args=[args]).start()


def win_proc_alive(name):
    """윈도우 프로세스가 살아있는지 확인합니다.
    Args:
        name: 프로세스 이름
    Returns:
        프로세스 생존 여부
    """
    import psutil
    alive = False
    for proc in psutil.process_iter():
        if name in proc.name():
            alive = True
    return alive


def pickle_write(file, data):
    """데이터를 피클 파일로 저장합니다.
    Args:
        file: 파일 이름
        data: 저장할 데이터
    """
    import _pickle
    with open(f'{file}.pkl', "wb") as f:
        _pickle.dump(data, f, protocol=-1)


def pickle_read(file):
    """피클 파일에서 데이터를 읽습니다.
    Args:
        file: 파일 이름
    Returns:
        읽은 데이터
    """
    import os
    import _pickle
    data = None
    if os.path.isfile(f'{file}.pkl'):
        with open(f'{file}.pkl', "rb") as f:
            data = _pickle.load(f)
    return data


def qtest_qwait(sec):
    """Qt 테스트 대기 시간을 설정합니다.
    Args:
        sec: 초
    """
    from PyQt5.QtTest import QTest
    # noinspection PyArgumentList
    QTest.qWait(int(sec * 1000))


def change_format(text, float_point=2):
    """텍스트 포맷을 변경합니다.
    Args:
        text: 텍스트
        float_point: 소수점 자리수
    Returns:
        포맷된 텍스트
    """
    text = str(text)
    try:
        format_data = f'{int(text):,}'
    except Exception:
        format_data = f'{float(text):,.{float_point}f}'
    return format_data


def floor_down(float_, decimal_point):
    """소수점 아래로 내림합니다.
    Args:
        float_: 실수
        decimal_point: 소수점
    Returns:
        내림된 실수
    """
    float_ = int(float_ * (1 / decimal_point))
    float_ = float_ * decimal_point
    return float_


def comma2int(t):
    """콤마가 포함된 문자열을 정수로 변환합니다.
    Args:
        t: 문자열
    Returns:
        정수
    """
    if '.' in t: t = t.split('.')[0]
    if '-' in t: t = t.replace('-', '')
    if ':' in t: t = t.replace(':', '')
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return int(t)


def comma2float(t):
    """콤마가 포함된 문자열을 실수로 변환합니다.
    Args:
        t: 문자열
    Returns:
        실수
    """
    if ' ' in t: t = t.replace(' ', '')
    if ',' in t: t = t.replace(',', '')
    return float(t)


def factorial(x):
    """팩토리얼을 계산합니다.
    Args:
        x: 숫자
    Returns:
        팩토리얼 값
    """
    if x <= 1: return 1
    result  = 1
    current = 2
    while current <= x:
        result *= current
        current += 1
    return result


def text_not_in_special_characters(t):
    """특수 문자가 포함되지 않았는지 확인합니다.
    Args:
        t: 텍스트
    Returns:
        특수 문자 포함 여부
    """
    import re
    t = t.replace(' ', '')
    if t == re.findall(r'\w+', t)[0]:
        return True
    return False


_UPBIT_HOGA_KEYS = (0.01, 1, 10, 100, 1000, 10000, 100000, 500000, 1000000, 2000000, float('inf'))
_UPBIT_HOGA_VALS = (0.0001, 0.001, 0.01, 0.1, 1, 5, 10, 50, 100, 500, 1000)


def get_hogaunit_coin(price):
    """코인 호가 단위를 반환합니다.
    Args:
        price: 가격
    Returns:
        호가 단위
    """
    import bisect
    idx = bisect.bisect_right(_UPBIT_HOGA_KEYS, price)
    return _UPBIT_HOGA_VALS[idx]


_HOGA_NEW_KEYS = (2000, 5000, 20000, 50000, 200000, 500000, float('inf'))
_HOGA_NEW_VALS = (1, 5, 10, 50, 100, 500, 1000)


def get_hogaunit_stock(price):
    """주식 호가 단위를 반환합니다.
    Args:
        price: 가격
    Returns:
        호가 단위
    """
    import bisect
    idx = bisect.bisect_right(_HOGA_NEW_KEYS, price)
    return _HOGA_NEW_VALS[idx]


def get_vi_price(std_price):
    """VI 가격을 계산합니다.
    Args:
        std_price: 기준 가격
    Returns:
        (상단 VI, 하단 VI, 호가 단위)
    """
    uvi = int(std_price * 1.1)
    x = get_hogaunit_stock(uvi)
    if uvi % x != 0:
        uvi += x - uvi % x
    dvi = int(std_price * 0.9)
    y = get_hogaunit_stock(dvi)
    if dvi % y != 0:
        dvi -= dvi % y
    return int(uvi), int(dvi), int(x)


def get_limit_price(predayclose):
    """상한가 하한가를 계산합니다.
    Args:
        predayclose: 전일 종가
    Returns:
        (상한가, 하한가)
    """
    uplimitprice = int(predayclose * 1.30)
    x = get_hogaunit_stock(uplimitprice)
    if uplimitprice % x != 0:
        uplimitprice -= uplimitprice % x
    downlimitprice = int(predayclose * 0.70)
    x = get_hogaunit_stock(downlimitprice)
    if downlimitprice % x != 0:
        downlimitprice += x - downlimitprice % x
    return int(uplimitprice), int(downlimitprice)
