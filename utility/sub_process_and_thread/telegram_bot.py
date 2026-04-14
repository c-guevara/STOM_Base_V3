
import pytz
import asyncio
import pandas as pd
from threading import Thread
from traceback import format_exc
from PyQt5.QtCore import QThread
from telegram.request import HTTPXRequest
from telegram import Update, ReplyKeyboardMarkup
from utility.settings.setting_base import ui_num
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes


class TelegramBot(QThread):
    """텔레그램 봇 클래스입니다.
    텔레그램 봇을 통해 메시지를 주고받습니다.
    """
    def __init__(self, qlist, dict_set):
        """텔레그램 봇을 초기화합니다.
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        Args:
            qlist: 큐 리스트
            dict_set: 설정 딕셔너리
        """
        super().__init__()
        self.windowQ       = qlist[0]
        self.teleQ         = qlist[3]
        self.traderQ       = qlist[9]
        self.stgQs         = qlist[10]
        self.dict_set      = dict_set

        self.token         = None
        self.chat_id       = None
        self.loop          = None
        self.application   = None
        self.message_queue = None
        self.running       = False

    def run(self):
        """텔레그램 봇을 실행합니다.
        """
        self.message_queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        Thread(target=self.moniter_queue, daemon=True).start()
        self.loop.create_task(self.process_messages())

        gubun = self.dict_set['거래소'][-2:]
        self.token = self.dict_set[f'텔레그램봇토큰{gubun}']
        self.chat_id = self.dict_set[f'텔레그램아이디{gubun}']

        if self.token and self.chat_id:
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
            )

            self.running = True
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .request(request)
                .post_init(self.setup_application)
                .build()
            )
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.loop.create_task(self.start_bot())

        self.loop.run_forever()

    async def start_bot(self):
        """봇을 시작합니다.
        """
        try:
            await self.application.initialize()
            await self.application.start()
            update_queue = await self.application.updater.start_polling()

            keyboard = [
                ['거래목록', '잔고평가', '잔고청산', '전략중지'],
                ['S라이브', 'F라이브', 'C라이브', 'B라이브']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard)

            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text='안녕하세요. STOM 텔레그램봇입니다.\n아래 버튼을 눌러 원하는 기능을 실행하세요.',
                reply_markup=reply_markup
            )

            while True:
                update = await update_queue.get()
                await self.application.process_update(update)
                update_queue.task_done()

        except:
            self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - start_bot'))
            self.running = False

    async def setup_application(self, application):
        """애플리케이션을 설정합니다.
        Args:
            application: 애플리케이션
        """
        korea_timezone = pytz.timezone('Asia/Seoul')
        application.bot_data['timezone'] = korea_timezone

    # noinspection PyUnusedLocal,PyUnresolvedReferences
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """메시지를 처리합니다.
        Args:
            update: 업데이트
            context: 컨텍스트
        """
        cmd = update.message.text
        cmd = cmd.replace('\n', '')
        if cmd == '전략중지':
            for q in self.stgQs:
                q.put('매수전략중지')
        elif '라이브' in cmd:
            self.windowQ.put(cmd)
        else:
            self.traderQ.put(cmd)

    def moniter_queue(self):
        """큐를 모니터링합니다.
        """
        while True:
            data = self.teleQ.get()
            if self.running or data.__class__ == tuple:
                self.loop.call_soon_threadsafe(self.message_queue.put_nowait, data)
            elif data.__class__ in (str, pd.DataFrame):
                if data == '스레드종료':
                    break
                self.windowQ.put((ui_num['시스템로그'], '텔레그램봇 토큰 및 아이디가 설정되지 않아 메세지를 보낼 수 없습니다'))

    async def process_messages(self):
        """메시지를 처리합니다.
        """
        while True:
            data = await self.message_queue.get()
            if data.__class__ == str:
                if '.png' in data:
                    await self.send_photo(data)
                else:
                    await self.send_message(data)
            elif isinstance(data.__class__, pd.DataFrame):
                await self.send_message(data.to_string())
            elif data.__class__ == tuple:
                self.dict_set = data[1]
                await self.restart_bot()
            self.message_queue.task_done()

    async def restart_bot(self):
        change = False
        gubun = self.dict_set['거래소'][-2:]
        if self.token != self.dict_set[f'텔레그램봇토큰{gubun}'] or \
                self.chat_id != self.dict_set[f'텔레그램아이디{gubun}']:
            change = True
            self.token = self.dict_set[f'텔레그램봇토큰{gubun}']
            self.chat_id = self.dict_set[f'텔레그램아이디{gubun}']

        if change:
            try:
                self.running = False
                if self.application and self.application.running:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                    self.application = None

                if self.token and self.chat_id:
                    self.running = True
                    self.application = (
                        ApplicationBuilder()
                        .token(self.token)
                        .post_init(self.setup_application)
                        .build()
                    )
                    self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                    await self.start_bot()
            except:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - restart_bot'))
                self.running = False

    async def send_message(self, text):
        if not self.running:
            return
        await self.application.bot.send_message(
            chat_id=self.chat_id,
            text=text
        )

    async def send_photo(self, photo_path):
        if not self.running:
            return
        with open(photo_path, 'rb') as photo:
            await self.application.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo
            )

    def stop(self):
        self.teleQ.put('스레드종료')
        if self.loop and self.loop.is_running():
            self.loop.stop()
