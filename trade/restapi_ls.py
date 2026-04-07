
import re
import json
import sqlite3
import asyncio
import requests
import websockets
import pandas as pd
from traceback import format_exc
from utility.static import str_ymd
from utility.setting_base import ui_num
from PyQt5.QtCore import QThread, pyqtSignal
from utility.static import now, timedelta_sec


class LsRestData:
    """LS증권 RESTAPI 데이터 클래스"""
    호스트주소 = 'https://openapi.ls-sec.co.kr:8080'
    웹소켓주소 = 'wss://openapi.ls-sec.co.kr:9443/websocket'
    마지막주소 = {
        '토큰발급': '/oauth2/token',
        '토큰폐기': '/oauth2/revoke',

        '국내주식종목정보': '/stock/etc',
        '국내주식예수금': '/stock/accno',
        '국내주식일반주문': '/stock/order',
        '국내주식정정주문': '/stock/order',
        '국내주식취소주문': '/stock/order',

        '지수선물종목정보1': '/futureoption/market-data',
        '지수선물종목정보2': '/futureoption/market-data',
        '지수선물예수금': '/futureoption/accno',
        '지수선물일반주문': '/futureoption/order',
        '지수선물정정주문': '/futureoption/order',
        '지수선물취소주문': '/futureoption/order',

        '야간선물종목정보': '/futureoption/market-data',
        '야간선물예수금': '/futureoption/accno',
        '야간선물일반주문': '/futureoption/order',
        '야간선물정정주문': '/futureoption/order',
        '야간선물취소주문': '/futureoption/order',

        '해외주식종목정보': '/overseas-stock/market-data',
        '해외주식예수금': '/overseas-stock/accno',
        '해외주식일반주문': '/overseas-stock/order',
        '해외주식정정주문': '/overseas-stock/order',

        '해외선물종목정보': '/overseas-futureoption/market-data',
        '해외선물예수금': '/overseas-futureoption/accno',
        '해외선물일반주문': '/overseas-futureoption/order',
        '해외선물정정주문': '/overseas-futureoption/order',
        '해외선물취소주문': '/overseas-futureoption/order'
    }

    당일일자 = str_ymd()
    장운영상태 = {
        11: '장전 동시호가가 시작되었습니다.',
        21: f'{당일일자[:4]}년 {당일일자[4:6]}월 {당일일자[6:8]}일 장이 시작되었습니다.',
        22: '장 시작 10초 전입니다.',
        23: '장 시작 1분 전입니다.',
        24: '장 시작 5분 전입니다.',
        25: '장 시작 10분 전입니다.',
        31: '장후 동시호가가 시작되었습니다.',
        41: f'{당일일자[:4]}년 {당일일자[4:6]}월 {당일일자[6:8]}일 장이 마감되었습니다.',
        42: '장 마감 10초 전입니다.',
        43: '장 마감 1분 전입니다.',
        44: '장 마감 5분 전입니다.'
    }

    장구분 = {
        1: '1',
        2: '1',
        3: '1',
        4: '9',
        6: '5',
        7: '8'
    }

    매매구분코드 = {
        '매도': '1',
        '매수': '2'
    }

    해외주식주문유형코드 = {
        '매도': '01',
        '매수': '02',
        '취소': '08'
    }

    국내주식호가유형코드 = {
        '지정가': '00',
        '시장가': '03',
        '조건부지정가': '05',
        '최유리지정가': '06',
        '최우선지정가': '10'
    }

    지수선물호가유형코드 = {
        '지정가': '00',
        '시장가': '03',
        '조건부지정가': '05',
        '최유리지정가': '06',
        '지정가IOC': '10',
        '지정가FOK': '20',
        '시장가IOC': '13',
        '시장가FOK': '23',
        '최유리지정가IOC': '16',
        '최유리지정가FOK': '26',
    }

    해외주식호가유형코드 = {
        '지정가': '00',
        'LOO': 'M1',
        'LOC': 'M2',
        '시장가': '03',
        'MOO': 'M3',
        'MOC': 'M4'
    }

    해외선물주문유형코드 = {
        '지정가': '1',
        '시장가': '2'
    }

    실시간거래코드 = {
        '장운영정보': 'JIF',

        '국내주식체결': 'US3',
        '국내주식호가': 'UH1',

        '지수선물체결': 'FC0',
        '지수선물호가': 'FH0',

        '야간선물체결': 'DC0',
        '야간선물호가': 'DH0',

        '해외주식체결': 'GSC',
        '해외주식호가': 'GSH',

        '해외선물체결': 'OVC',
        '해외선물호가': 'OVH',
    }

    주문거래코드 = {
        '국내주식주문접수': 'SC0',
        '국내주식주문체결': 'SC1',
        '국내주식주문정정': 'SC2',
        '국내주식주문취소': 'SC3',
        '국내주식주문거부': 'SC4',

        '지수선물주문접수': 'O01',
        '지수선물주문체결': 'C01',
        '지수선물주문정정취소': 'H01',

        '야간선물주문접수': 'O02',
        '야간선물주문체결': 'C02',
        '야간선물주문정정취소': 'H02',

        '해외주식주문접수': 'AS0',
        '해외주식주문체결': 'AS1',
        '해외주식주문정정': 'AS2',
        '해외주식주문취소': 'AS3',
        '해외주식주문거부': 'AS4',

        '해외선물주문접수': 'TC1',
        '해외선물주문응답': 'TC2',
        '해외선물주문체결': 'TC3'
    }

    tr_data = {
        '국내주식종목정보': {
            'tr_cd': 't8436',
            'body_key': 't8436InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8436OutBlock'
        },
        '국내주식예수금': {
            'tr_cd': 'CSPAQ12200',
            'body_key': 'CSPAQ12200InBlock1',
            'element_keys': ['RecCnt', 'BalCreTp'],
            'element_values': ['레코드갯수', '잔고생성구분'],
            'out_block': 'CSPAQ12200OutBlock2'
        },
        '국내주식일반주문': {
            'tr_cd': 'CSPAT00601',
            'body_key': 'CSPAT00601InBlock1',
            'element_keys': ['IsuNo', 'OrdQty', 'OrdPrc', 'BnsTpCode', 'OrdprcPtnCode', 'MgntrnCode', 'LoanDt',
                             'OrdCndiTpCode', 'MbrNo'],
            'element_values': ['종목코드', '주문수량', '주문가격', '매매구분', '호가유형코드', '신용거래코드', '대출일', '주문조건구분',
                               '회원사번호'],
            'out_block': 'CSPAT00601OutBlock2'
        },
        '국내주식정정주문': {
            'tr_cd': 'CSPAT00701',
            'body_key': 'CSPAT00701InBlock1',
            'element_keys': ['OrgOrdNo', 'IsuNo', 'OrdQty', 'OrdprcPtnCode', 'OrdCndiTpCode', 'OrdPrc'],
            'element_values': ['원주문번호', '종목코드', '주문수량', '호가유형코드', '주문조건구분', '주문가격'],
            'out_block': 'CSPAT00701OutBlock2'
        },
        '국내주식취소주문': {
            'tr_cd': 'CSPAT00801',
            'body_key': 'CSPAT00801InBlock1',
            'element_keys': ['OrgOrdNo', 'IsuNo', 'OrdQty'],
            'element_values': ['원주문번호', '종목코드', '주문수량'],
            'out_block': 'CSPAT00801OutBlock2'
        },

        '지수선물종목정보1': {
            'tr_cd': 't8432',
            'body_key': 't8432InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8432OutBlock'
        },
        '지수선물종목정보2': {
            'tr_cd': 't8435',
            'body_key': 't8435InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8435OutBlock'
        },
        '지수선물예수금': {
            'tr_cd': 'CFOBQ10500',
            'body_key': 'CFOBQ10500InBlock1',
            'element_keys': ['RecCnt'],
            'element_values': ['레코드갯수'],
            'out_block': 'CFOBQ10500OutBlock2'
        },
        '지수선물일반주문': {
            'tr_cd': 'CFOAT00100',
            'body_key': 'CFOAT00100InBlock1',
            'element_keys': ['FnoIsuNo', 'BnsTpCode', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'OrdQty'],
            'element_values': ['종목코드', '매매구분코드', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CFOAT00100OutBlock2'
        },
        '지수선물정정주문': {
            'tr_cd': 'CFOAT00200',
            'body_key': 'CFOAT00200InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'MdfyQty'],
            'element_values': ['종목코드', '원주문번호', '호가유형코드', '주문가격', '정정수량'],
            'out_block': 'CFOAT00200OutBlock2'
        },
        '지수선물취소주문': {
            'tr_cd': 'CFOAT00300',
            'body_key': 'CFOAT00300InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'CancQty'],
            'element_values': ['종목코드', '원주문번호', '취소수량'],
            'out_block': 'CFOAT00300OutBlock2'
        },

        '야간선물종목정보': {
            'tr_cd': 't8455',
            'body_key': 't8455InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 't8455OutBlock'
        },
        '야간선물예수금': {
            'tr_cd': 'CFOBQ10500',
            'body_key': 'CFOBQ10500InBlock1',
            'element_keys': ['RecCnt'],
            'element_values': ['레코드갯수'],
            'out_block': 'CFOBQ10500OutBlock2'
        },
        '야간선물일반주문': {
            'tr_cd': 'CCENT00100',
            'body_key': 'CCENT00100InBlock1',
            'element_keys': ['FnoIsuNo', 'BnsTpCode', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'OrdQty'],
            'element_values': ['종목코드', '매매구분코드', '호가유형코드', '주문가격', '주문수량'],
            'out_block': 'CCENT00100OutBlock2'
        },
        '야간선물정정주문': {
            'tr_cd': 'CCENT00200',
            'body_key': 'CCENT00200InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'FnoOrdprcPtnCode', 'FnoOrdPrc', 'MdfyQty'],
            'element_values': ['종목코드', '원주문번호', '호가유형코드', '주문가격', '정정수량'],
            'out_block': 'CCENT00200OutBlock2'
        },
        '야간선물취소주문': {
            'tr_cd': 'CCENT00300',
            'body_key': 'CCENT00300InBlock1',
            'element_keys': ['FnoIsuNo', 'OrgOrdNo', 'CancQty'],
            'element_values': ['종목코드', '원주문번호', '취소수량'],
            'out_block': 'CCENT00300OutBlock2'
        },

        '해외주식종목정보': {
            'tr_cd': 'g3190',
            'body_key': 'g3190InBlock',
            'element_keys': ['delaygb', 'natcode', 'exgubun', 'readcnt', 'cts_value'],
            'element_values': ['지연구분', '국가구분', '거래소구분', '조회갯수', '연속구분'],
            'out_block': 'g3190OutBlock1'
        },
        '해외주식예수금': {
            'tr_cd': 'COSOQ02701',
            'body_key': 'COSOQ02701InBlock1',
            'element_keys': ['RecCnt', 'CrcyCode'],
            'element_values': ['레코드갯수', '통화코드'],
            'out_block': 'COSOQ02701OutBlock3'
        },
        '해외주식일반주문': {
            'tr_cd': 'COSAT00301',
            'body_key': 'COSAT00301InBlock1',
            'element_keys': ['RecCnt', 'OrdPtnCode', 'OrgOrdNo', 'OrdMktCode', 'IsuNo', 'OrdQty', 'OvrsOrdPrc',
                             'OrdprcPtnCode', 'BrkTpCode'],
            'element_values': ['레코드갯수', '주문유형코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격',
                               '호가유형코드', '중개인구분코드'],
            'out_block': 'COSAT00301OutBlock2'
        },
        '해외주식정정주문': {
            'tr_cd': 'COSAT00311',
            'body_key': 'COSAT00311InBlock1',
            'element_keys': ['RecCnt', 'OrdPtnCode', 'OrgOrdNo', 'OrdMktCode', 'IsuNo', 'OrdQty', 'OvrsOrdPrc',
                             'OrdprcPtnCode', 'BrkTpCode'],
            'element_values': ['레코드갯수', '주문유형코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격',
                               '호가유형코드', '중개인구분코드'],
            'out_block': 'COSAT00311OutBlock2'
        },

        '해외선물종목정보': {
            'tr_cd': 'o3101',
            'body_key': 'o3101InBlock',
            'element_keys': ['gubun'],
            'element_values': ['구분'],
            'out_block': 'o3101OutBlock'
        },
        '해외선물예수금': {
            'tr_cd': 'CIDBQ03000',
            'body_key': 'CIDBQ03000InBlock1',
            'element_keys': ['AcntTpCode', 'TrdDt'],
            'element_values': ['계좌구분코드', '거래일자'],
            'out_block': 'CIDBQ03000OutBlock2'
        },
        '해외선물일반주문': {
            'tr_cd': 'CIDBT00100',
            'body_key': 'CIDBT00100InBlock1',
            'element_keys': ['OrdDt', 'IsuCodeVal', 'FutsOrdTpCode', 'BnsTpCode', 'AbrdFutsOrdPtnCode',
                             'CrcyCode', 'OvrsDrvtOrdPrc', 'CndiOrdPrc', 'OrdQty', 'PrdtCode', 'DueYymm', 'ExchCode'],
            'element_values': ['주문일자', '종목코드', '주문구분코드', '매매구분코드', '주문유형코드', '통화코드', '주문가격',
                               '조건주문가격', '주문수량', '상품코드', '만기년월', '거래소코드'],
            'out_block': 'CIDBT00100OutBlock2'
        },
        '해외선물정정주문': {
            'tr_cd': 'CIDBT00900',
            'body_key': 'CIDBT00900InBlock1',
            'element_keys': ['OrdDt', 'OvrsFutsOrgOrdNo', 'IsuCodeVal', 'FutsOrdTpCode', 'BnsTpCode', 'FutsOrdPtnCode',
                             'CrcyCodeVal', 'OvrsDrvtOrdPrc', 'CndiOrdPrc', 'OrdQty', 'OvrsDrvtPrdtCode', 'DueYymm',
                             'ExchCode'],
            'element_values': ['주문일자', '원주문번호', '종목코드', '주문구분코드', '매매구분코드', '주문유형코드', '통화코드',
                               '주문가격', '조건주문가격', '주문수량', '상품코드', '만기년월', '거래소코드'],
            'out_block': 'CIDBT00900OutBlock2'
        },
        '해외선물취소주문': {
            'tr_cd': 'CIDBT01000',
            'body_key': 'CIDBT01000InBlock1',
            'element_keys': ['OrdDt', 'IsuCodeVal', 'OvrsFutsOrgOrdNo', 'FutsOrdTpCode', 'PrdtTpCode', 'ExchCode'],
            'element_values': ['주문일자', '종목코드', '원주문번호', '주문구분코드', '상품구분코드', '거래소코드'],
            'out_block': 'CIDBT01000OutBlock2'
        }
    }


class LsRestAPI:
    """ LS증권 RESTAPI 메인 클래스 - 국내주식, 지수선물, 미국주식, 해외선물 모두 지원"""
    def __init__(self, windowQ, access, secret):
        self.windowQ = windowQ
        self.access  = access
        self.secret  = secret
        self.token   = None
        self.tr_cont = False
        self.tr_cont_key = ''

    def _post(self, gubun: str, cont='N', cont_key='', **kwargs):
        """요청용 데이터(url, headers, params) 생성 및 전송
        인자:
            gubun: TR한글이름
            cont: 연속조회여부
            cont_key: 연속조회키
            **kwargs: TR별 키워드 - LsRestData.tr_data에 미리 선언해두고 조합한다."""
        url = f'{LsRestData.호스트주소}{LsRestData.마지막주소[gubun]}'
        if gubun == '토큰발급':
            headers = {
                'content-type': 'application/x-www-form-urlencoded'
            }
            params = {
                'grant_type': 'client_credentials',
                'appkey': self.access,
                'appsecretkey': self.secret,
                'scope': 'oob'
            }
        else:
            tr_data = LsRestData.tr_data[gubun]
            headers = {
                'content-type': 'application/json; charset=utf-8',
                'authorization': f'Bearer {self.token}',
                'tr_cd': tr_data['tr_cd'],
                'tr_cont': cont,
                'tr_cont_key': cont_key
            }
            body_key = str(tr_data['body_key'])
            element_keys = tr_data['element_keys']
            element_values = [kwargs[k] for k in tr_data['element_values']]
            params = {body_key: dict(zip(element_keys, element_values))}

        self.tr_cont = False
        self.tr_cont_key = ''

        if gubun == '토큰발급':
            response = requests.post(url, headers=headers, params=params)
        else:
            response = requests.post(url, headers=headers, data=json.dumps(params))

        self.tr_cont = True if response.headers.get('tr_cont') == 'Y' else False
        self.tr_cont_key = response.headers.get('tr_cont_key')

        return response.json()

    def create_token(self):
        """토큰 발급"""
        data = self._post('토큰발급')
        self.token = data['access_token']
        return self.token

    def get_code_info_stock(self, etfgubun=0):
        """국내주식종목정보 ['구분']
        etfgubun: 0 (코스피 + 코스닥), 1 (ETF), 2 (ETN)
        공통사항: data['shcode'][-1] == '0' (우선주제외), data['spac_gubun'] == 'N' (스펙 제외)"""
        tr_name = '국내주식종목정보'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='0')
        dict_data = {}
        for data in data[out_block]:
            gubun = int(data['etfgubun'])
            if etfgubun == gubun and data['shcode'][-1] == '0' and data['spac_gubun'] == 'N':
                dict_data[data['shcode']] = {'종목명': data['hname']}
        return dict_data, list(dict_data.keys())

    def get_code_info_future(self):
        """지수선물종목정보1 ['구분'], 지수선물종목정보2 ['구분']
        코스피200(t8432), 코스닥150(t8435) 조회 TR이 다름 - 구분: '' (코스피200선물), 'SF' (코스닥150선물)"""
        data_list = []
        tr_name = '지수선물종목정보1'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='')
        data_list.extend(data[out_block])
        tr_name = '지수선물종목정보2'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='SF')
        data_list.extend(data[out_block])
        dict_data = {}
        for data in data_list:
            종목코드 = data['shcode']
            종목명 = '코스닥150' if 'KQF' in data['hname'] else '코스피200'
            if 종목코드.startswith('A'):
                dict_data[종목코드] = {'종목명': 종목명}
        return dict_data, list(dict_data.keys())

    def get_code_info_future_night(self):
        """야간선물종목정보 ['구분'], 구분: 'NF' (코스피200선물), 'NQF' (코스닥150선물)"""
        data_list = []
        tr_name = '야간선물종목정보'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='NFU')
        data_list.extend(data[out_block])
        tr_name = '야간선물종목정보'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='NQF')
        data_list.extend(data[out_block])
        dict_data = {}
        for data in data_list:
            종목코드 = data['shcode']
            종목명 = '코스닥150' if 'KQF' in data['hname'] else '코스피200'
            if 종목코드.startswith('A'):
                dict_data[종목코드] = {'종목명': 종목명}
        return dict_data, list(dict_data.keys())

    def get_code_info_stock_usa(self):
        """해외주식종목정보 ['지연구분', '국가구분', '거래소구분', '조회갯수', '연속구분']
        거래소구분: '1' (뉴욕거래소), '2' (나스닥)
        제외: 우선주, 채권, 워런트, ADR, 유닛, 종목명이 영문인 종목, 종목코드에 '-', '.' 이 포함된 종목"""
        tr_name = '해외주식종목정보'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data_list = []
        data = self._post(tr_name, 지연구분='R', 국가구분='US', 거래소구분='1', 조회갯수=9999, 연속구분='')
        data_list.extend(data[out_block])
        data = self._post(tr_name, 지연구분='R', 국가구분='US', 거래소구분='2', 조회갯수=9999, 연속구분='')
        data_list.extend(data[out_block])
        keysymbols = []
        dict_data = {}
        korean_pattern = re.compile(r'[\uAC00-\uD7A3]')
        for data in data_list:
            code = data['symbol']
            name = data['korname']
            if not bool(korean_pattern.search(name)) or '-' in code or '.' in code or '유닛' in name or \
                    '채권' in name or '우선주' in name or '워런트' in name or '(ADR)' in name:
                continue
            keysymbols.append(data['keysymbol'])
            dict_data[data['symbol']] = {
                '종목명': data['korname'],
                '거래소코드': data['exchcd'],
                '상장주식수': int(data['share'])
            }
        return dict_data, keysymbols

    def get_code_info_future_oversea(self):
        """해외선물종목정보 ['구분']"""
        tr_name = '해외선물종목정보'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 구분='')
        dict_data = {}
        for data in data[out_block]:
            dict_data[data['Symbol']] = {
                '종목명': data['SymbolNm'],
                '위탁증거금': int(float(data['OpngMgn'])),
                '호가단위': float(data['UntPrc']),
                '틱가치': float(data['MnChgAmt']),
                '소숫점자리수': data['DotGb']
            }
        return dict_data, list(dict_data.keys())

    def get_balance_stock(self):
        """국내주식예수금 ['레코드갯수', '잔고생성구분']"""
        tr_name = '국내주식예수금'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 레코드갯수=1, 잔고생성구분='1')
        return int(data[out_block]['D2Dps'])

    def get_balance_future(self):
        """지수선물예수금 ['레코드갯수']"""
        tr_name = '지수선물예수금'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 레코드갯수=1)
        return int(data[out_block]['Dps'])

    def get_balance_stock_usa(self):
        """해외주식예수금 ['레코드갯수', '통화코드']"""
        tr_name = '해외주식예수금'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 레코드갯수=1, 통화코드='USD')
        return int(data[out_block]['FcurrDps'])

    def get_balance_future_oversea(self):
        """ 해외선물예수금 ['계좌구분코드', '거래일자']"""
        tr_name = '해외선물예수금'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 계좌구분코드='1', 거래일자=LsRestData.당일일자)
        return int(data[out_block]['FcurrOrdAbleAmt'])

    def order_stock(self, 종목코드, 매매구분, 주문수량, 주문가격, 호가유형):
        """국내주식일반주문
        ['종목코드', '주문수량', '주문가격', '매매구분', '호가유형코드', '신용거래코드', '대출일', '주문조건구분', '회원사번호']"""
        tr_name = '국내주식일반주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        매매구분코드 = LsRestData.매매구분코드[매매구분]
        호가유형코드 = LsRestData.국내주식호가유형코드[호가유형]
        data = self._post(tr_name, 종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 매매구분=매매구분코드, 호가유형코드=호가유형코드,
                          신용거래코드='000', 대출일='', 주문조건구분='0', 회원사번호='')
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_modify_stock(self, 원주문번호, 종목코드, 주문수량, 호가유형, 주문가격):
        """국내주식정정주문 ['원주문번호', '종목코드', '주문수량', '호가유형코드', '주문조건구분', '주문가격']"""
        tr_name = '국내주식정정주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        호가유형코드 = LsRestData.국내주식호가유형코드[호가유형]
        data = self._post(tr_name, 원주문번호=원주문번호, 종목코드=종목코드, 주문수량=주문수량, 호가유형코드=호가유형코드, 주문조건구분='0',
                          주문가격=주문가격)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_cancel_stock(self, 원주문번호, 종목코드, 주문수량):
        """국내주식취소주문 ['원주문번호', '종목코드', '주문수량']"""
        tr_name = '국내주식취소주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 원주문번호=원주문번호, 종목코드=종목코드, 주문수량=주문수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_future(self, 종목코드, 매매구분, 호가유형, 주문가격, 주문수량):
        """지수선물일반주문 ['종목코드', '매매구분코드', '호가유형코드', '주문가격', '주문수량']"""
        tr_name = '지수선물일반주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        매매구분코드 = LsRestData.매매구분코드[매매구분]
        호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
        data = self._post(tr_name, 종목코드=종목코드, 매매구분코드=매매구분코드, 호가유형코드=호가유형코드, 주문가격=주문가격,
                          주문수량=주문수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_modify_future(self, 종목코드, 원주문번호, 호가유형, 주문가격, 정정수량):
        """지수선물정정주문 ['종목코드', '원주문번호', '호가유형코드', '주문가격', '정정수량']"""
        tr_name = '지수선물정정주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
        data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 호가유형코드=호가유형코드, 주문가격=주문가격, 정정수량=정정수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_cancel_future(self, 종목코드, 원주문번호, 취소수량):
        """지수선물취소주문 ['종목코드', '원주문번호', '취소수량']"""
        tr_name = '지수선물취소주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 취소수량=취소수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_future_night(self, 종목코드, 매매구분, 호가유형, 주문가격, 주문수량):
        """야간선물일반주문 ['종목코드', '매매구분코드', '호가유형코드', '주문가격', '주문수량']"""
        tr_name = '야간선물일반주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        매매구분코드 = LsRestData.매매구분코드[매매구분]
        호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
        data = self._post(tr_name, 종목코드=종목코드, 매매구분코드=매매구분코드, 호가유형코드=호가유형코드, 주문가격=주문가격,
                          주문수량=주문수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_modify_future_night(self, 종목코드, 원주문번호, 호가유형, 주문가격, 정정수량):
        """야간선물정정주문 ['종목코드', '원주문번호', '호가유형코드', '주문가격', '정정수량']"""
        tr_name = '야간선물정정주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
        data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 호가유형코드=호가유형코드, 주문가격=주문가격, 정정수량=정정수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_cancel_future_night(self, 종목코드, 원주문번호, 취소수량):
        """야간선물취소주문 ['종목코드', '원주문번호', '취소수량']"""
        tr_name = '야간선물취소주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 취소수량=취소수량)
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_stock_usa(self, 주문유형, 주문시장코드, 종목코드, 주문수량, 주문가격, 호가유형, 원주문번호=''):
        """해외주식일반주문
        ['레코드갯수', '주문유형코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격', '호가유형코드', '중개인구분코드']"""
        tr_name = '해외주식일반주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        주문유형코드 = LsRestData.해외주식주문유형코드[주문유형]
        호가유형코드 = LsRestData.해외주식호가유형코드[호가유형]
        if 주문유형 in ('매수', '매도'):
            data = self._post(tr_name, 레코드갯수=1, 주문유형코드=주문유형코드, 주문시장코드=주문시장코드, 종목코드=종목코드,
                              주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
        else:
            data = self._post(tr_name, 레코드갯수=1, 주문유형코드=주문유형코드, 원주문번호=원주문번호, 주문시장코드=주문시장코드,
                              종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_modify_stock_usa(self, 주문유형, 원주문번호, 주문시장코드, 종목코드, 주문수량, 주문가격, 호가유형):
        """해외주식정정주문
        ['레코드갯수', '주문유형코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격', '호가유형코드', '중개인구분코드']"""
        tr_name = '해외주식정정주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        주문유형코드 = LsRestData.해외주식주문유형코드[주문유형]
        호가유형코드 = LsRestData.해외주식호가유형코드[호가유형]
        data = self._post(tr_name, 레코드갯수=1, 주문유형코드=주문유형코드, 원주문번호=원주문번호, 주문시장코드=주문시장코드,
                          종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
        return data[out_block]['OrdNo'], data['rsp_msg']

    def order_future_oversea(self, 종목코드, 매매구분, 주문유형, 주문가격, 주문수량, 조건주문가격):
        """해외선물일반주문
        ['주문일자', '종목코드', '주문구분코드', '매매구분코드', '주문유형코드', '통화코드', '주문가격', '조건주문가격', '주문수량',
        '상품코드', '만기년월', '거래소코드']"""
        tr_name = '해외선물일반주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        매매구분코드 = LsRestData.매매구분코드[매매구분]
        주문유형코드 = LsRestData.해외선물주문유형코드[주문유형]
        data = self._post(tr_name, 주문일자=LsRestData.당일일자, 종목코드=종목코드, 주문구분코드='1', 매매구분코드=매매구분코드,
                          주문유형코드=주문유형코드, 통화코드=' ',  주문가격=주문가격, 조건주문가격=조건주문가격,
                          주문수량=주문수량, 상품코드='000000', 만기년월='000001', 거래소코드=' ')
        return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']

    def order_modify_future_oversea(self, 원주문번호, 종목코드, 매매구분, 주문유형, 주문가격, 조건주문가격, 주문수량):
        """해외선물정정주문
        ['주문일자', '원주문번호', '종목코드', '주문구분코드', '매매구분코드', '주문유형코드', '통화코드', '주문가격', '조건주문가격',
        '주문수량', '상품코드', '만기년월', '거래소코드']"""
        tr_name = '해외선물정정주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        매매구분코드 = LsRestData.매매구분코드[매매구분]
        주문유형코드 = LsRestData.해외선물주문유형코드[주문유형]
        data = self._post(tr_name, 주문일자=LsRestData.당일일자, 원주문번호=원주문번호, 종목코드=종목코드, 주문구분코드='2',
                          매매구분코드=매매구분코드, 주문유형코드=주문유형코드, 통화코드=' ', 주문가격=주문가격,
                          조건주문가격=조건주문가격, 주문수량=주문수량, 상품코드='', 만기년월='', 거래소코드=' ')
        return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']

    def order_cancel_future_oversea(self, 종목코드, 원주문번호):
        """해외선물취소주문 ['주문일자', '종목코드', '원주문번호', '주문구분코드', '상품구분코드', '거래소코드']"""
        tr_name = '해외선물취소주문'
        out_block = LsRestData.tr_data[tr_name]['out_block']
        data = self._post(tr_name, 주문일자=LsRestData.당일일자, 종목코드=종목코드, 원주문번호=원주문번호, 주문구분코드='3',
                          상품구분코드=' ', 거래소코드=' ')
        return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']


class WebSocketReceiver(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, gubun, token, symbols, windowQ):
        super().__init__()
        self.gubun     = gubun
        self.token     = token
        self.symbols   = symbols
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run())
        self.loop.run_forever()

    async def _run(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    asyncio.create_task(self._real_reg())
                await self._receive_message()
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - WebSocketReceiver'))

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(LsRestData.웹소켓주소, ping_timeout=60, ping_interval=60)
        self.connected = True

    async def _receive_message(self):
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            if data['body']:
                self.signal.emit(data)

    async def _real_reg(self):
        운영등록완료 = False if self.gubun != '해외선물' else True
        체결등록완료 = False
        호가등록완료 = False
        등록완료번호 = 0
        등록할총개수 = len(self.symbols)
        다음등록시간 = now()

        while not self.connected:
            await asyncio.sleep(0.1)

        while self.connected:
            if not 운영등록완료:
                data = self._get_send_data('장운영정보', '실시간시세등록', '0')
                await self.websocket.send(json.dumps(data))
                다음등록시간 = timedelta_sec(2)
                운영등록완료 = True

            elif not 체결등록완료:
                if now() > 다음등록시간:
                    gubun = f'{self.gubun}체결'
                    for code in self.symbols[등록완료번호:등록완료번호 + 100]:
                        data = self._get_send_data(gubun, '실시간시세등록', code)
                        await self.websocket.send(json.dumps(data))

                    다음등록시간 = timedelta_sec(2)
                    등록완료번호 = 등록완료번호 + 100
                    self.windowQ.put(
                        (ui_num['기본로그'], f'{gubun} 실시간시세 등록 [{min(등록완료번호, 등록할총개수)}/{등록할총개수}]')
                    )
                    if 등록완료번호 >= 등록할총개수:
                        체결등록완료 = True
                        등록완료번호 = 0

            elif not 호가등록완료:
                if now() > 다음등록시간:
                    gubun = f'{self.gubun}호가'
                    for code in self.symbols[등록완료번호:등록완료번호 + 100]:
                        data = self._get_send_data(gubun, '실시간시세등록', code)
                        await self.websocket.send(json.dumps(data))

                    다음등록시간 = timedelta_sec(2)
                    등록완료번호 = 등록완료번호 + 100
                    self.windowQ.put(
                        (ui_num['기본로그'], f'{gubun} 실시간시세 등록 [{min(등록완료번호, 등록할총개수)}/{등록할총개수}]')
                    )
                    if 등록완료번호 >= 등록할총개수:
                        break

    def _get_send_data(self, gubun: str, tr_type: str, code: str):
        if '국내주식' in gubun:
            tr_key = f'U{code:<9}'
        elif '해외주식' in gubun:
            tr_key = f'{code:<18}'
        else:
            tr_key = code

        data = {
            'header': {
                'token': self.token,
                'tr_type': '3' if tr_type == '실시간시세등록' else '4'
            },
            'body': {
                'tr_cd': LsRestData.실시간거래코드[gubun],
                'tr_key': tr_key
            }
        }
        return data

    async def _disconnect(self):
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(1)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class WebSocketTrader(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, gubun, token, windowQ):
        super().__init__()
        self.gubun     = gubun
        self.token     = token
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run())
        self.loop.run_forever()

    async def _run(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                await self._receive_message()
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - WebSocketTrader'))

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(LsRestData.웹소켓주소, ping_timeout=60, ping_interval=60)
        self.connected = True
        for gubun in LsRestData.주문거래코드:
            if self.gubun in gubun:
                data = self._get_send_data(gubun, '계좌등록')
                await self.websocket.send(json.dumps(data))
                self.windowQ.put((ui_num['기본로그'], f'{gubun} 실시간시세 계좌등록'))

    async def _receive_message(self):
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            if data['body']:
                self.signal.emit(data)

    def _get_send_data(self, gubun: str, tr_type: str):
        data = {
            'header': {
                'token': self.token,
                'tr_type': '1' if tr_type == '계좌등록' else '2'
            },
            'body': {
                'tr_cd': LsRestData.주문거래코드[gubun],
                'tr_key': ''
            }
        }
        return data

    async def _disconnect(self):
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(1)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class Writer(QThread):
    signal = pyqtSignal(str)

    def __init__(self, windowQ):
        super().__init__()
        self.windowQ = windowQ

    def run(self):
        while True:
            data = self.windowQ.get()
            self.signal.emit(data[1])


if __name__ == "__main__":
    """테스트 코드"""
    import sys
    from multiprocessing import Queue
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    gubun_ = '국내주식'  # 국내주식, 국내주식ETF, 국내주식ETN, 지수선물, 야간선물, 해외주식, 해외선물
    access_key = 'PSRFkgSSsFHFZ5scUWeEd6dFnw5cqbdCA3gk'
    secret_key = 'dp9q92cFbpxMaTARhE3jSJOipCtTc2Gl'

    windowQ_ = Queue()

    ls = LsRestAPI(windowQ_, access_key, secret_key)
    token_ = ls.create_token()

    conn = sqlite3.connect('code_info.db')
    if gubun_ == '국내주식':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=0)
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('stock_info', conn, if_exists='replace')
    elif gubun_ == '국내주식ETF':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=1)
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('stock_etf_info', conn, if_exists='replace')
    elif gubun_ == '국내주식ETN':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=2)
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('stock_etn_info', conn, if_exists='replace')
    elif gubun_ == '지수선물':
        dict_info, symbols_ = ls.get_code_info_future()
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('future_info', conn, if_exists='replace')
    elif gubun_ == '야간선물':
        dict_info, symbols_ = ls.get_code_info_future_night()
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('future_night_info', conn, if_exists='replace')
    elif gubun_ == '해외주식':
        dict_info, symbols_ = ls.get_code_info_stock_usa()
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('stock_us_info', conn, if_exists='replace')
    else:
        dict_info, symbols_ = ls.get_code_info_future_oversea()
        df = pd.DataFrame.from_dict(dict_info, orient='index')
        df.to_sql('future_os_info', conn, if_exists='replace')
    conn.close()

    def real_data_print(data):
        print(f'[{now()}] {data}')

    writer = Writer(windowQ_)
    writer.signal.connect(real_data_print)
    writer.start()

    ws_thread = WebSocketReceiver(gubun_, token_, symbols_, windowQ_)
    ws_thread.signal.connect(real_data_print)
    ws_thread.start()

    app.exec_()
