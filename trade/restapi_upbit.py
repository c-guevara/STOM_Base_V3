
import re
import jwt
import json
import uuid
import hashlib
import asyncio
import requests
import websockets
from traceback import format_exc
from urllib.parse import unquote, urlencode
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import ui_num


def get_symbols_info():
    dict_data = {}
    headers = {'accept': 'application/json'}

    url = 'https://api.upbit.com/v1/market/all'
    response = requests.get(url, headers=headers)
    datas = response.json()
    for data in datas:
        symbol = data['market']
        if 'KRW' in symbol:
            dict_data[symbol] = {
                '종목명': data['korean_name']
            }

    url = 'https://api.upbit.com/v1/ticker/all?quote_currencies=KRW'
    response = requests.get(url, headers=headers)
    datas = response.json()
    for data in datas:
        symbol = data['market']
        dict_data[symbol].update({
            '거래대금':  int(data['acc_trade_price'])
        })

    return dict_data, list(dict_data.keys())


class UpbitRestAPI:
    def __init__(self, access, secret):
        self.access = access
        self.secret = secret

        self.주문구분 = {
            '매수': 'bid',
            '매도': 'ask'
        }

        self.주문유형 = {
            '시장가': {'매수': 'price', '매도': 'market'},
            '지정가': {'매수': 'limit', '매도': 'limit'},
            '지정가IOC': {'매수': 'limit', '매도': 'limit'},
            '지정가FOK': {'매수': 'limit', '매도': 'limit'},
            '최유리IOC': {'매수': 'best', '매도': 'best'},
            '최유리FOK': {'매수': 'best', '매도': 'best'},
        }

        self.주문조건 = {
            '지정가IOC': 'ioc',
            '지정가FOK': 'fok',
            '최유리IOC': 'ioc',
            '최유리FOK': 'fok',
        }

    def _headers(self, query=None):
        payload = {
            'access_key': self.access,
            'nonce': str(uuid.uuid4())
        }
        if query is not None:
            query_string = unquote(urlencode(query, doseq=True))
            query_hash = hashlib.sha512(query_string.encode('utf-8')).hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        token = jwt.encode(payload, self.secret, algorithm='HS512')
        if not isinstance(token, str):
            token = token.decode('utf-8')

        return {'Authorization': f'Bearer {token}'}

    def _get(self, url, data=None):
        headers = self._headers(data)
        response = requests.get(url, headers=headers, data=data)
        return response.json()

    def _post(self, url, data):
        headers = self._headers(data)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()

    def _delete(self, url, data):
        headers = self._headers(data)
        response = requests.delete(url, headers=headers, data=json.dumps(data))
        return response.json()

    def get_balances(self):
        url = 'https://api.upbit.com/v1/accounts'
        ret = self._get(url)
        return int(float(ret[0]['balance']))

    def order_coin(self, 종목코드='', 주문구분='', 주문유형='', 주문금액=0, 주문수량=0):
        url = 'https://api.upbit.com/v1/orders'
        data = {
            'market': 종목코드,
            'side': self.주문구분[주문구분],
            'ord_type': self.주문유형[주문유형][주문구분]
        }

        if 주문구분 == '매수' or '지정가' in 주문유형:
            data['price'] = str(주문금액)

        if 주문수량 > 0 and (주문구분 == '매도' or '지정가' in 주문유형):
            data['volume'] = str(주문수량)

        주문조건 = self.주문조건.get(주문유형)
        if 주문조건:
            data['time_in_force'] = 주문조건

        return self._post(url, data)

    def order_cancel(self, od_no):
        url = 'https://api.upbit.com/v1/order'
        data = {'uuid': od_no}
        return self._delete(url, data)

    def get_order_info(self, od_no, state='wait', page=1, limit=100):
        p = re.compile(r'^\w+-\w+-\w+-\w+-\w+$')
        is_uuid = len(p.findall(od_no)) > 0
        if is_uuid:
            url = 'https://api.upbit.com/v1/order'
            data = {'uuid': od_no}
        else:
            url = 'https://api.upbit.com/v1/orders'
            data = {'market': od_no, 'state': state, 'page': page, 'limit': limit, 'order_by': 'desc'}
        return self._get(url, data)


class UpbitWebSocketReceiver(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.codes     = codes
        self.windowQ   = windowQ
        self.loop      = None
        self.wsk_trade = None
        self.wsk_order = None
        self.con_trade = False
        self.con_order = False
        self.url       = 'wss://api.upbit.com/websocket/v1'

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.run_trade())
        self.loop.create_task(self.run_order())
        self.loop.run_forever()

    async def run_trade(self):
        while True:
            try:
                if not self.con_trade:
                    await self.connect_trader()
                await self.receive_ticker()
            except:
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 실시간체결 수신 중 오류가 발생하여 재연결합니다.')
                )

            await self.disconnect_trader()

    async def run_order(self):
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except:
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 실시간호가 수신 중 오류가 발생하여 재연결합니다.')
                )

            await self.disconnect_order()

    async def connect_trader(self):
        self.con_trade = True
        self.wsk_trade = await websockets.connect(self.url, ping_interval=60)
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_trade.send(json.dumps(data))

    async def connect_order(self):
        self.con_order = True
        self.wsk_order = await websockets.connect(self.url, ping_interval=60)
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_order.send(json.dumps(data))

    async def receive_ticker(self):
        while self.con_trade:
            data = await self.wsk_trade.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def receive_order(self):
        while self.con_order:
            data = await self.wsk_order.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def disconnect_trader(self):
        self.con_trade = False
        if self.wsk_trade is not None:
            await self.wsk_trade.close()
        await asyncio.sleep(5)

    async def disconnect_order(self):
        self.con_order = False
        if self.wsk_order is not None:
            await self.wsk_order.close()
        await asyncio.sleep(5)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class UpbitWebSocketTrader(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, windowQ):
        super().__init__()
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False
        self.url       = 'wss://api.upbit.com/websocket/v1/private'

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
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 주문체결 수신 중 오류가 발생하여 재연결합니다.')
                )

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(self.url, ping_interval=60)
        self.connected = True
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'myOrder'}]
        await self.websocket.send(json.dumps(data))

    async def _receive_message(self):
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def _disconnect(self):
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(5)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()
