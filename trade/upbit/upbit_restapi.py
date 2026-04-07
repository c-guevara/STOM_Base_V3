
import re
import jwt
import json
import uuid
import hashlib
import asyncio
import requests
import websockets
from traceback import format_exc
from urllib.parse import urlencode
from utility.setting_base import ui_num
from PyQt5.QtCore import QThread, pyqtSignal


def get_symbols_info():
    url = 'https://api.upbit.com/v1/ticker/all?quote_currencies=KRW'
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    data = response.json()
    dict_data = {}
    for d in data:
        dict_data[d['market']] = int(d['acc_trade_price'])
    return dict_data, list(dict_data.keys())


class Upbit:
    def __init__(self, access, secret):
        self.access = access
        self.secret = secret

    def _request_headers(self, query=None):
        payload = {
            'access_key': self.access,
            'nonce': str(uuid.uuid4())
        }

        if query is not None:
            m = hashlib.sha512()
            m.update(urlencode(query, doseq=True).replace('%5B%5D=', '[]=').encode())
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        jwt_token = jwt.encode(payload, self.secret, algorithm='HS256')
        authorization_token = 'Bearer {}'.format(jwt_token)
        headers = {'Authorization': authorization_token}
        return headers

    def _get(self, url, data=None):
        headers = self._request_headers(data)
        response = requests.get(url, headers=headers, data=data)
        return response.json()

    def _post(self, url, data):
        headers = self._request_headers(data)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()

    def _delete(self, url, data):
        headers = self._request_headers(data)
        response = requests.delete(url, headers=headers, data=json.dumps(data))
        return response.json()

    def get_balances(self):
        url = 'https://api.upbit.com/v1/accounts'
        return self._get(url)

    def buy_market_order(self, ticker, price):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'bid', 'price': str(price), 'ord_type': 'price'}
        return self._post(url, data)

    def buy_limit_order(self, ticker, price, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'bid', 'volume': str(volume), 'price': str(price), 'ord_type': 'limit'}
        return self._post(url, data)

    def sell_market_order(self, ticker, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'ask', 'volume': str(volume), 'ord_type': 'market'}
        return self._post(url, data)

    def sell_limit_order(self, ticker, price, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'ask', 'volume': str(volume), 'price': str(price), 'ord_type': 'limit'}
        return self._post(url, data)

    def cancel_order(self, od_no):
        url = 'https://api.upbit.com/v1/order'
        data = {'uuid': od_no}
        return self._delete(url, data)

    def get_order(self, od_no, state='wait', page=1, limit=100):
        p = re.compile(r'^\w+-\w+-\w+-\w+-\w+$')
        is_uuid = len(p.findall(od_no)) > 0
        if is_uuid:
            url = 'https://api.upbit.com/v1/order'
            data = {'uuid': od_no}
        else:
            url = 'https://api.upbit.com/v1/orders'
            data = {'market': od_no, 'state': state, 'page': page, 'limit': limit, 'order_by': 'desc'}
        return self._get(url, data)


class WebSocketReceiver(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.codes     = codes
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False
        self.url       = 'wss://api.upbit.com/websocket/v1'

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
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 수신 중 오류가 발생하여 재연결합니다.')
                )

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(self.url, ping_interval=60)
        self.connected = True
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.websocket.send(json.dumps(data))
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
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
