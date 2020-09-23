import asyncio
import os,time
import signal,sys
import xml.sax.saxutils as xmlutil
from concurrent.futures import CancelledError
import multiprocessing

import blivedm.blivedm as blivedm
import utils

class BLiveXMLlogger(blivedm.BLiveClient):
    def __init__(self, room_id, uid=0, heartbeat_interval=30, ssl=True, loop=None):
        super().__init__(room_id, uid=uid, heartbeat_interval=heartbeat_interval, ssl=ssl, loop=loop)
        self.room_id_log = room_id
        self.saving_file = None
        self.async_proc = None

    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        #print(f'{danmaku.uname}：{danmaku.msg}')
        curtime = danmaku.timestamp/1000
        self.saving_file.write(f'<d p="{curtime-self.init_time},{danmaku.mode},{danmaku.font_size},{danmaku.color},{int(curtime)},0,{danmaku.uid},0">{xmlutil.escape(danmaku.msg)}</d>')
        self.saving_file.flush()

    async def _on_super_chat(self, message: blivedm.SuperChatMessage):
        #print(f'醒目留言 ¥{message.price} {message.uname}：{message.message}')
        #danmaku type: 1 - normal, 4 - bottom, 5 - top, 6 - reverse, 7 - special(unknown), 8 - hidden
        curtime = message.start_time
        color = int(message.background_color[1:],16)
        self.saving_file.write(f'<d p="{curtime-self.init_time},5,35,{color},{int(curtime)},0,{message.uid},0">{xmlutil.escape(message.uname)}(¥{message.price}): {xmlutil.escape(message.message)}</d>')
        self.saving_file.flush()

    def run_cancellable(self):
        try:
            self.async_loop.run_until_complete(self.start())
        except CancelledError:
            pass

    def run(self, saving_path='sample.xml'):
        self.saving_path = saving_path
        xmlheader = '''<?xml version="1.0" encoding="UTF-8"?><i><chatserver>chat.bilibili.com</chatserver><chatid>0</chatid><mission>0</mission><maxlimit>10000000</maxlimit><state>0</state><real_name>0</real_name><source>k-v</source>'''
        self.saving_file = open(self.saving_path,'a')
        self.saving_file.write(xmlheader)
        self.saving_file.flush()
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
        xmltail = '''</i>'''
        self.saving_file.write(xmltail)
        self.saving_file.close()
        utils.print_log(self.room_id_log, '弹幕保存完成'+self.saving_path)
