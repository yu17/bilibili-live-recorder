from Live import BiliBiliLive
import blivedm_xml_logger as dmxml
import blivedm_lar_logger as dmlar
import json
import os, sys, signal
import requests
import time
import utils
import re
import multiprocessing, threading
import urllib3
urllib3.disable_warnings()

# youtube-url https://www.youtube.com/embed/live_stream?channel=UC8NZiqKx6fsDT3AVcMiVFyA&autoplay=1

class BiliBiliLiveRecorder(BiliBiliLive):
    def __init__(self, room_id, enable_inform = False, inform_url = '', check_interval = 300, saving_path = 'files', use_cookies = False, cookies_file = None, capture_danmaku = True, capture_from_youtube = False, youtube_channel_id = ""):
        super().__init__(room_id)
        self.enable_inform = enable_inform
        self.inform_url = inform_url
        self.last_inform = 0
        self.check_interval = check_interval
        self.saving_path = saving_path if os.path.isabs(saving_path) else os.path.join(os.getcwd(), saving_path)
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
        self.capture_danmaku = capture_danmaku
        self.capture_from_youtube = capture_from_youtube
        self.youtube_channel_id = youtube_channel_id
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
            if not resp.ok:
                raise Exception("Stream not available. Received code "+str(resp.status_code))
            with open(os.path.join(self.saving_path, self.fname+'.flv'), "ab") as f:
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
                    if self.capture_danmaku:
                        self.dmlogger = dmxml.BLiveXMLlogger(self.room_id, uid=0)
                        self.dmlogger.run(saving_path = os.path.join(self.saving_path, self.fname+'.xml'))
                        self.lalogger = dmlar.BLiveLARlogger(self.room_id, uid=0)
                        self.lalogger.run(saving_path = os.path.join(self.saving_path, self.fname+'.lar'))
                    self.stream_rec_thread = threading.Thread(target = self.record, args = (res[0],))
                    self.stream_rec_thread.start()
                if res:
                    if self.recording_lock.acquire(timeout = self.check_interval):
                        self.stream_rec_thread.join()
                        if self.capture_danmaku:
                            self.dmlogger.terminate()
                            del self.dmlogger
                            self.lalogger.terminate()
                            del self.lalogger
                        self.recording_lock.release()
                else:
                    time.sleep(self.check_interval)
        except Exception as e:
            utils.print_log(self.room_id, 'Error while checking or recording:' + str(e))
        finally:
            if self.recording_lock.locked() and self.capture_danmaku:
                self.dmlogger.terminate()
                del self.dmlogger
                self.lalogger.terminate()
                del self.lalogger
                self.recording_lock.release()

def signal_handler(sig, frame):
    glob_vars = frame.f_back.f_back.f_back.f_locals
#    glob_vars = frame
#    while glob_vars is not None and glob_vars.f_locals is not None and 'recording_rooms' not in glob_vars.f_locals.keys():
#        glob_vars = glob_vars.f_back

#    if glob_vars is not None and glob_vars.f_locals is not None and 'recording_rooms' in glob_vars.f_locals.keys():
#        glob_vars = glob_vars.f_locals
#        print(glob_vars['recording_rooms'])
    if 'recording_rooms' in glob_vars.keys():
        for i in glob_vars['room_processors']:
            i.terminate()
            i.join()
    exit(0)
#    else:
#        time.sleep(1)
#        sys.exit(0)

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
        room['capture_danmaku'] if 'capture_danmaku' in room.keys() else default['capture_danmaku'],
        room['capture_from_youtube'] if 'capture_from_youtube' in room.keys() else default['capture_from_youtube'],
        room['youtube_channel_id'] if 'youtube_channel_id' in room.keys() else default['youtube_channel_id']
        ) for room in config['rooms']]
    
    room_processors = [multiprocessing.Process(target=i.run) for i in recording_rooms]

    for i in room_processors:
        i.start()
    for i in room_processors:
        i.join()

#    for proc in room_processors:
#        proc.start()
#    while True:
#        for i,proc in enumerate(room_processors):
#            if not proc.is_alive():
#                print(recording_rooms[i].room_id,'is dead!!')
#                proc.join()
#                room_processors[i] = multiprocessing.Process(target=recording_rooms[i].run)
#        time.sleep(300)
