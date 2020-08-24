from Live import BiliBiliLive
import os, sys
import requests
import time
import utils
import re
import multiprocessing
import urllib3
urllib3.disable_warnings()

import json


class BiliBiliLiveRecorder(BiliBiliLive):
    def __init__(self, room_id, enable_inform = False, inform_url = '', check_interval = 300, saving_path = 'files', use_cookies = False, cookies_file = None, capture_danmaku = True):
        super().__init__(room_id)
        self.enable_inform = enable_inform
        self.inform_url = inform_url
        self.check_interval = check_interval
        self.saving_path = saving_path
        if use_cookies:
            try:
                self.load_cookies(cookies_file)
            except Exception as e:
                utils.print_log(self.room_id, 'Error when loading cookies: ', str(e), '\nWarning:  Continuing without cookies!')
                self.cookies = None

    def check(self, interval):
        while True:
            try:
                self.room_info = self.get_room_info()
                if self.room_info['status']:
                    utils.inform(self.room_id, self.room_info['roomname'], self.enable_inform, self.inform_url)
                    utils.print_log(self.room_id, self.room_info['roomname'])
                    break
                else:
                    utils.print_log(self.room_id, '等待开播')
            except Exception as e:
                utils.print_log(self.room_id, 'Error:' + str(e))
            time.sleep(interval)
        return self.get_live_urls()

    def check_running(self, interval):
        while True:
            try:
                self.room_info = self.get_room_info()
                if self.room_info['status']:
                    utils.print_log(self.room_id, self.room_info['roomname'])
                else:
                    break
            except Exception as e:
                utils.print_log(self.room_id, 'Error:' + str(e))
                break
            time.sleep(interval)

    def record(self, record_url, output_filename, interval):
        try:
            utils.print_log(self.room_id, '√ 正在录制...' + self.room_id)
            headers = dict()
            headers['Accept-Encoding'] = 'identity'
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko'
            headers['Referer'] = re.findall(r'(https://.*\/).*\.flv', record_url)[0]
            resp = requests.get(record_url, stream=True, headers=headers)
            status_checker = mp(target=self.check_running,args=(interval,))
            status_checker.start()
            with open(output_filename, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk) if chunk else None
            status_checker.terminate()
            status_checker.join()
        except Exception as e:
            utils.print_log(self.room_id, 'Error while recording:' + str(e))
            status_checker.join()

    def run(self):
        while True:
            try:
                urls = self.check(interval=self.check_interval)
                filename = utils.generate_filename(self.room_id,self.room_info['roomname'])
                if os.path.isabs(saving_path):
                    c_filename = os.path.join(saving_path, filename)
                else:
                    c_filename = os.path.join(os.getcwd(), saving_path, filename)
                print(c_filename)
                self.record(urls[0], c_filename, self.check_interval)
                utils.print_log(self.room_id, '录制完成' + c_filename)
            except Exception as e:
                utils.print_log(self.room_id, 'Error while checking or recording:' + str(e))


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

    config = json.load(open(config_path,'r'))
    default = config['default']

    mp = multiprocessing.Process
    recording_rooms = [mp(target=BiliBiliLiveRecorder(
        room['room_id'],
        room['enable_inform'] if 'enable_inform' in room.keys() else default['enable_inform'],
        room['inform_url'] if 'inform_url' in room.keys() else default['inform_url'],
        room['check_interval'] if 'check_interval' in room.keys() else default['check_interval'],
        room['saving_path'] if 'saving_path' in room.keys() else default['saving_path'],
        room['use_cookies'] if 'use_cookies' in room.keys() else default['use_cookies'],
        room['cookies_file'] if 'cookies_file' in room.keys() else default['cookies_file'],
        room['capture_danmaku'] if 'capture_danmaku' in room.keys() else default['capture_danmaku']
        ).run) for room in config['rooms']]
    for i in recording_rooms:
        i.start()
    for i in recording_rooms:
        i.join()
