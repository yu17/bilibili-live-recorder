import time
import requests


def get_current_time(time_format):
    current_struct_time = time.localtime(time.time())
    current_time = time.strftime(time_format, current_struct_time)
    return current_time


def generate_filename(room_id, room_name):
    data = dict()
    data['c_time'] = get_current_time('%Y%m%d_%H%M')
    data['room_id'] = room_id
    data['roomname'] = room_name.replace('/','-').replace('\\','-')
    return '_'.join(data.values())


def inform(room_id, desp, inform_url = ''):
    param = {
        'text': '直播间：{} 开始直播啦！'.format(room_id),
        'desp': desp,
    }
    resp = requests.get(url=inform_url, params=param)
    print_log(room_id=room_id, content='通知完成！') if resp.status_code == 200 else None


def print_log(room_id='None', content='None'):
    brackets = '[{}]'
    time_part = brackets.format(get_current_time('%Y-%m-%d %H:%M:%S'))
    room_part = brackets.format('直播间: ' + str(room_id))
    print(time_part, room_part, content)
