from Live import BiliBiliLive
import os, sys
import requests
import time
import config
import utils
import re
import multiprocessing
import urllib3
urllib3.disable_warnings()


class BiliBiliLiveRecorder(BiliBiliLive):
    def __init__(self, room_id, check_interval=5*60, saving_path = 'files'):
        super().__init__(room_id)
        self.inform = utils.inform
        self.print = utils.print_log
        self.check_interval = check_interval
        self.saving_path = saving_path

    def check(self, interval):
        while True:
            try:
                self.room_info = self.get_room_info()
                if self.room_info['status']:
                    self.inform(room_id=self.room_id,desp=self.room_info['roomname'])
                    self.print(self.room_id, self.room_info['roomname'])
                    break
                else:
                    self.print(self.room_id, '等待开播')
            except Exception as e:
                self.print(self.room_id, 'Error:' + str(e))
            time.sleep(interval)
        return self.get_live_urls()

    def check_running(self, interval):
        while True:
            try:
                self.room_info = self.get_room_info()
                if self.room_info['status']:
                    self.print(self.room_id, self.room_info['roomname'])
                else:
                    break
            except Exception as e:
                self.print(self.room_id, 'Error:' + str(e))
                break
            time.sleep(interval)

    def record(self, record_url, output_filename, interval):
        try:
            self.print(self.room_id, '√ 正在录制...' + self.room_id)
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
            self.print(self.room_id, 'Error while recording:' + str(e))
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
                self.print(self.room_id, '录制完成' + c_filename)
            except Exception as e:
                self.print(self.room_id, 'Error while checking or recording:' + str(e))


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 2:
        input_id = [str(sys.argv[1])]
        saving_path = 'files'
    elif len(sys.argv) == 1:
        input_id = config.rooms
        saving_path = config.default_saving_path
    else:
        raise ZeroDivisionError('请检查输入的命令是否正确 例如：python3 run.py 10086')

    mp = multiprocessing.Process
    tasks = [mp(target=BiliBiliLiveRecorder(room_id, 300, saving_path).run) for room_id in input_id]
    for i in tasks:
        i.start()
    for i in tasks:
        i.join()
