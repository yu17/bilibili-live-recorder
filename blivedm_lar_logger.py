import asyncio
import os,time
import signal,sys
import xml.sax.saxutils as xmlutil
from concurrent.futures import CancelledError
import multiprocessing

import blivedm.blivedm as blivedm
import utils

class BLiveLARlogger(blivedm.BLiveClient):
    def __init__(self, room_id, uid=0, heartbeat_interval=30, ssl=True, loop=None):
        super().__init__(room_id, uid=uid, heartbeat_interval=heartbeat_interval, ssl=ssl, loop=loop)
        self.room_id_log = room_id
        self.saving_file = None
        self.async_proc = None

    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()

    async def __on_vip_enter(self, command):
        print(command)
    _COMMAND_HANDLERS['WELCOME'] = __on_vip_enter  # 老爷入场

    async def _on_receive_popularity(self, popularity: int):
        curtime = time.time()
        self.saving_file.write(f'[{int(curtime*1000)}][POP]({curtime-self.init_time:.3f}){popularity}\n')
        self.saving_file.flush()

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        curtime = danmaku.timestamp/1000
        self.saving_file.write(f'[{danmaku.timestamp}][DANMAKU]({curtime-self.init_time:.3f},{danmaku.mode},{danmaku.font_size},{danmaku.color},{danmaku.msg_type})<{danmaku.uid},"{xmlutil.escape(danmaku.uname)}",{danmaku.user_level},{danmaku.ulevel_color},{xmlutil.escape(str(danmaku.ulevel_rank))},{danmaku.privilege_type},{danmaku.admin},{danmaku.vip},{danmaku.svip},{danmaku.urank},{danmaku.uname_color}><{xmlutil.escape(danmaku.medal_name)},{danmaku.medal_level},{danmaku.room_id},"{xmlutil.escape(danmaku.runame)}",{danmaku.mcolor},{danmaku.special_medal}>{xmlutil.escape(danmaku.msg)}\n')
        self.saving_file.flush()

    async def _on_receive_gift(self, gift: blivedm.GiftMessage):
        self.saving_file.write(f'[{gift.timestamp*1000}][GIFT]({gift.timestamp-self.init_time:.3f},{gift.gift_name},{gift.gift_id},{gift.gift_type},{gift.num},{gift.action},{gift.price})<{gift.uid},"{gift.uname}",{gift.guard_level}>{gift.coin_type},{gift.total_coin}\n')
        self.saving_file.flush()

    async def _on_buy_guard(self, message: blivedm.GuardBuyMessage):
        curtime = time.time()
        self.saving_file.write(f'[{int(curtime*1000)}][GUARD]({curtime-self.init_time:.3f},{message.gift_name},{message.gift_id},{message.num},{message.price})<{message.uid},"{xmlutil.escape(message.username)}",{message.guard_level}>{message.start_time},{message.end_time}\n')
        self.saving_file.flush()

    async def _on_super_chat(self, message: blivedm.SuperChatMessage):
        #danmaku type: 1 - normal, 4 - bottom, 5 - top, 6 - reverse, 7 - special(unknown), 8 - hidden
        curtime = message.start_time
        color = int(message.background_color[1:],16)
        pricecolor = int(message.background_price_color[1:],16)
        self.saving_file.write(f'[{curtime*1000}][SUPERCHAT]({curtime-self.init_time:.3f},{message.gift_name},{message.gift_id},{color},{pricecolor},{message.start_time},{message.end_time},{message.time},{message.price})<{message.uid},"{xmlutil.escape(message.uname)}",{message.user_level},{message.guard_level}>{xmlutil.escape(message.message)}\n')
        self.saving_file.flush()

    def run_cancellable(self):
        try:
            self.async_loop.run_until_complete(self.start())
        except CancelledError:
            pass

    def run(self, saving_path='sample.lar'):
        self.saving_path = saving_path
        self.saving_file = open(self.saving_path,'a')
        self.init_time = time.time()

        self.async_loop = asyncio.get_event_loop()
        self.async_proc = multiprocessing.Process(target=self.run_cancellable)
        self.async_proc.start()

    def terminate(self):
        if self.is_running:
            future = self.stop()
            future.add_done_callback(lambda _future: asyncio.ensure_future(self.close()))
        else:
            asyncio.ensure_future(self.close())
        #self.async_loop.stop()
        self.async_proc.terminate()
        self.async_proc.join()
        self.saving_file.close()
        utils.print_log(self.room_id_log, 'Live Activity Record saved at '+self.saving_path)
