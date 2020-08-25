import asyncio
import os,time
import signal,sys

import blivedm.blivedm as blivedm

import multiprocessing

class BLiveXMLlogger(blivedm.BLiveClient):
    def __init__(self, room_id, uid=0, heartbeat_interval=30, ssl=True, loop=None, saving_path='sample.xml', init_time=int(time.time())):
        super().__init__(room_id, uid=uid, heartbeat_interval=heartbeat_interval, ssl=ssl, loop=loop)
        self.saving_path = saving_path
        self.init_time = init_time

        self.saving_file = None
        self.async_proc = None

    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        #print(f'{danmaku.uname}：{danmaku.msg}')
        curtime = danmaku.timestamp//1000
        self.saving_file.write(f'<d p="{curtime-self.init_time},{danmaku.mode},{danmaku.font_size},{danmaku.color},{curtime},0,{danmaku.uid},0">{danmaku.msg}</d>')
        self.saving_file.flush()

    async def _on_super_chat(self, message: blivedm.SuperChatMessage):
        #print(f'醒目留言 ¥{message.price} {message.uname}：{message.message}')
        curtime = message.start_time//1000
        self.saving_file.write(f'<d p="{curtime-self.init_time},2,45,{message.background_color},{curtime},0,{message.uid},0">{message.uname}(¥{message.price}): {message.message}</d>')
        self.saving_file.flush()

    def init(self):
        xmlheader = '''<?xml version="1.0" encoding="UTF-8"?><i><chatserver>chat.bilibili.com</chatserver><chatid>0</chatid><mission>0</mission><maxlimit>10000000</maxlimit><state>0</state><real_name>0</real_name><source>k-v</source>'''
        self.saving_file = open(self.saving_path,'w')
        self.saving_file.write(xmlheader)
        self.saving_file.flush()

    def run(self):
        async_loop = asyncio.get_event_loop()
        self.async_proc = multiprocessing.Process(target=async_loop.run_until_complete,args=(self.start(),))
        self.async_proc.start()

    def terminate(self):
        self.async_proc.terminate()
        self.async_proc.join()
        xmltail = '''</i>'''
        self.saving_file.write(xmltail)
        self.saving_file.close()

# sample main() to run the logger
if __name__ == '__main__':
    logger = BLiveXMLlogger(21449083,saving_path = 'sample.xml')
    logger.init()
    logger.run()
    time.sleep(10)
    logger.terminate()

#asyncio.get_event_loop().run_until_complete(logger.run())
    
