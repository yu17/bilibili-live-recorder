from Live import BiliBiliLive
import blivedm_xml_logger as dmxml
import json
import os, sys, signal
import requests
import time
import utils
import re
import multiprocessing, threading
import urllib3
urllib3.disable_warnings()


class BiliBiliLiveRecorder(BiliBiliLive):
    def __init__(self, room_id, enable_inform = False, inform_url = '', check_interval = 300, saving_path = 'files', use_cookies = False, cookies_file = None, capture_danmaku = True):
        super().__init__(room_id)
        self.enable_inform = enable_inform
        self.inform_url = inform_url
        self.last_inform = 0
        self.check_interval = check_interval
        if os.path.isabs(saving_path):
            self.saving_path = saving_path
        else:
            self.saving_path = os.path.join(os.getcwd(), saving_path)
        if not os.path.exists(saving_path):
            utils.print_log(self.room_id, f'Warning: The saving path does not exist! Creating directories: {self.saving_path}')
            try:
                os.makedirs(self.saving_path)
            except Exception as e:
                utils.print_log(self.room_id, f'Error: Failed to create directories: {self.saving_path}: {str(e)}\nPlease check if the path is writable and set to the proper permissions.')
                return None
        if use_cookies:
            try:
                self.load_cookies(cookies_file)
            except Exception as e:
                utils.print_log(self.room_id, f'Error when loading cookies: {str(e)}\nWarning:  Continuing without cookies!')
                self.cookies = None
        self.recording_lock = threading.Lock()

    def check(self):
        try:
            self.room_info = self.get_room_info()
            if self.room_info['status']:
                utils.print_log(self.room_id, self.room_info['roomname'])
                if self.recording_lock.locked():
                    return True
                else:
                    # Calls inform only when it is enabled and no inform was sent in the last 100 secs
                    # This prevents unexpectedly spamming the infrom service in edge cases, for example, when the streamer had a bad network connnection or the streamer didn't turn off live after disconnection.
                    if self.enable_inform and time.time()-self.last_inform>100:
                        utils.inform(self.room_id, self.room_info['roomname'], self.inform_url)
                        self.last_inform = time.time()
                    return self.get_live_urls()
            else:
                utils.print_log(self.room_id, '等待开播')
                return False
        except Exception as e:
            utils.print_log(self.room_id, 'Error:' + str(e))
        return False

    def record(self, record_url):
        self.recording_lock.acquire()
        try:
            utils.print_log(self.room_id, '√ 正在录制...' + self.room_info['roomname'])
            headers = dict()
            headers['Accept-Encoding'] = 'identity'
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko'
            headers['Referer'] = re.findall(r'(https://.*\/).*\.flv', record_url)[0]
            resp = requests.get(record_url, stream=True, headers=headers)
            with open(os.path.join(self.saving_path, self.fname+'.flv'), "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk) if chunk else None
        except Exception as e:
            utils.print_log(self.room_id, 'Error while recording:' + str(e))
        finally:
            utils.print_log(self.room_id, '录制完成'+self.fname+'.flv')
            self.recording_lock.release()

    def run(self):
        try:
            while True:
                res = self.check()
                if isinstance(res, list):
                    self.fname = utils.generate_filename(self.room_id,self.room_info['roomname'])
                    self.dmlogger = dmxml.BLiveXMLlogger(self.room_id, uid=0, saving_path = os.path.join(self.saving_path, self.fname+'.xml'))
                    self.dmlogger.init()
                    self.dmlogger.run()
                    self.stream_rec_thread = threading.Thread(target = self.record, args = (res[0],))
                    self.stream_rec_thread.start()
                    time.sleep(self.check_interval)
                elif res:
                    if self.recording_lock.acquire(timeout = self.check_interval):
                        self.stream_rec_thread.join()
                        self.dmlogger.terminate()
                else:
                    time.sleep(self.check_interval)
        except Exception as e:
            utils.print_log(self.room_id, 'Error while checking or recording:' + str(e))
        finally:
            if self.recording_lock.locked():
                self.dmlogger.terminate()

def signal_handler(sig, frame):
    glob_vars = frame.f_back.f_back.f_back.f_locals
    if 'recording_rooms' in glob_vars.keys():
        for i in glob_vars['room_processors']:
            i.terminate()
            i.join()
    exit(0)

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '-c':
        config_path = sys.argv[2]
    elif len(sys.argv) == 1:
        config_path = 'config.json'
    else:
        print('Usage: ', sys.argv[0], ' [-c CONFIG_FILE]')
        exit(1)
    if not os.path.exists(config_path):
        print(config_path,' does not exist!')
        exit(2)

    signal.signal(signal.SIGINT, signal_handler)

    config = json.load(open(config_path,'r'))
    default = config['default']

    recording_rooms = [BiliBiliLiveRecorder(
        room['room_id'],
        room['enable_inform'] if 'enable_inform' in room.keys() else default['enable_inform'],
        room['inform_url'] if 'inform_url' in room.keys() else default['inform_url'],
        room['check_interval'] if 'check_interval' in room.keys() else default['check_interval'],
        room['saving_path'] if 'saving_path' in room.keys() else default['saving_path'],
        room['use_cookies'] if 'use_cookies' in room.keys() else default['use_cookies'],
        room['cookies_file'] if 'cookies_file' in room.keys() else default['cookies_file'],
        room['capture_danmaku'] if 'capture_danmaku' in room.keys() else default['capture_danmaku']
        ) for room in config['rooms']]
    
    room_processors = [multiprocessing.Process(target=i.run) for i in recording_rooms]

    for i in room_processors:
        i.start()
    for i in room_processors:
        i.join()
