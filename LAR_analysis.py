#!/usr/bin/python

import datetime as dt
import os,sys
import re
import time
from collections import deque

import matplotlib.cbook as cbook
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

# Data classes. Used for detail data storage.

class BiliUser:
    def __init__(self,uid,uname,guard,ulevel=None,ulevel_color=None,ulevel_rank=None):
        self.uid = int(uid)
        self.uname = uname
        self.guard = int(guard)
        self.ulevel = int(ulevel) if ulevel and ulevel.isdigit else ulevel
        self.ulevel_color = ulevel_color
        self.ulevel_rank = ulevel_rank

class BiliDanmaku(BiliUser):
    def __init__(self,time_abs,time_rel,danmaku_mode,danmaku_fs,danmaku_color,danmaku_type,uid,uname,ulevel,ulevel_color,ulevel_rank,guard,uadmin,uvip,usvip,urank,uname_color,medal_name,medal_level,medal_rid,medal_uname,medal_color,medal_special,danmaku_text):
        BiliUser.__init__(self,uid,uname,guard,ulevel=ulevel,ulevel_color=ulevel_color,ulevel_rank=ulevel_rank)
        self.time_abs = time_abs
        self.time_rel = time_rel
        self.danmaku_mode = danmaku_mode
        self.danmaku_fs = danmaku_fs
        self.danmaku_color = danmaku_color
        self.danmaku_type = danmaku_type
        self.uadmin = uadmin
        self.uvip = uvip
        self.usvip = usvip
        self.urank = urank
        self.uname_color = uname_color
        self.medal_name = medal_name
        self.medal_level = medal_level
        self.medal_rid = medal_rid
        self.medal_uname = medal_uname
        self.medal_color = medal_color
        self.medal_special = medal_special
        self.danmaku_text = danmaku_text

class BiliGift(BiliUser):
    def __init__(self,time_abs,time_rel,gift_name,gift_id,gift_type,gift_count,gift_action,gift_price,uid,uname,guard,gift_coin_type,gift_coin_count):
        BiliUser.__init__(self,uid,uname,guard)
        self.time_abs = time_abs
        self.time_rel = time_rel
        self.gift_name = gift_name
        self.gift_id = gift_id
        self.gift_type = gift_type
        self.gift_count = gift_count
        self.gift_price = gift_price
        self.gift_coin_type = gift_coin_type
        self.gift_coin_count = gift_coin_count

class BiliGuard(BiliGift):
    def __init__(self,time_abs,time_rel,guard_name,guard_id,guard_count,guard_price,uid,uname,guard,guard_ss,guard_to):
        BiliGift.__init__(self,time_abs,time_rel,guard_name,guard_id,None,guard_count,None,guard_price,uid,uname,guard,'gold',guard_count*guard_price)
        self.guard_ss = guard_ss
        self.guard_to = guard_to

class BiliSC(BiliUser):
    def __init__(self,time_abs,time_rel,SC_name,SC_id,SC_color,SC_pricecolor,SC_ss,SC_to,SC_duration,SC_price,uid,uname,ulevel,guard,SC_text):
        BiliUser.__init__(self,uid,uname,guard,ulevel=ulevel)
        self.time_abs = time_abs
        self.time_rel = time_rel
        self.SC_name = SC_name
        self.SC_id = SC_id
        self.SC_color = SC_color
        self.SC_pricecolor = SC_pricecolor
        self.SC_ss = SC_ss
        self.SC_to = SC_to
        self.SC_duration = SC_duration
        self.SC_price = SC_price
        self.SC_text = SC_text

class LARParse:
    def __init__(self):
        self.stampreg = re.compile(r'\[(\d+?)\]\[([A-Z]+?)\]\((.+?)\)')
        self.danreg = re.compile(r'<(.*?)><(.*?)>(.*)')
        self.giftreg = re.compile(r'<(.*?)>(.*)')
        self.smartcomma = re.compile(r''',(?=(?:[^'"]|'[^']*'|"[^"]*")*$)''')
        self.resolution = 60
        self.report_generation_flag = 0
        self.concatenate = False
        self.POPULARITY_FREQ = 30 # Popularity is updated at fixed rate of /30s

    def stats_init(self,timestamp):
        self.individual_users = []
        self.total_danmaku = 0
        self.total_income = 0
        self.total_income_gift = 0
        self.total_income_sc = 0
        self.total_guards = 0
        self.total_guards_l3 = 0
        self.total_guards_l2 = 0
        self.total_guards_l1 = 0
        self.max_pop = 0
        self.trend_danmaku = []
        self.trend_gift_paid = []
        self.trend_gift_free = []
        self.trend_sc = []
        self.trend_guard = []
        self.trend_pop = []
        self.trend_pop_count = []
        self.cache_danmaku = deque()
        self.cache_gift_paid = deque()
        self.cache_gift_free = deque()
        self.cache_sc = deque()
        self.cache_guard = deque()
        self.cache_pop = deque()
        self.reltime = 0.0
        self.abstime = 0.0
        self.abstime_start = timestamp

    def stats_wrapup(self):
        self.reltime_end = self.reltime
        self.abstime_end = self.abstime
        self.max_trend_len = (self.abstime_end-self.abstime_start)//1000//self.resolution+1
        while len(self.trend_danmaku)<self.max_trend_len:
            self.trend_danmaku.append(0)
        while len(self.trend_gift_paid)<self.max_trend_len:
            self.trend_gift_paid.append(0)
        while len(self.trend_gift_free)<self.max_trend_len:
            self.trend_gift_free.append(0)
        while len(self.trend_sc)<self.max_trend_len:
            self.trend_sc.append(0)
        while len(self.trend_guard)<self.max_trend_len:
            self.trend_guard.append(0)
        while len(self.trend_pop)<self.max_trend_len:
            self.trend_pop.append(0)
            self.trend_pop_count.append(0)
        self.trend_pop_count=np.array(self.trend_pop_count)
        self.trend_pop_count[self.trend_pop_count==0] = 1
        self.xtick_width=min((self.max_trend_len//200+1)*5,60)

    def stats_genreport_text(self,filename):
        with open(filename,'w') as f:
            totaltime = (self.abstime_end-self.abstime_start)//1000
            f.write(f'直播时长,{totaltime//3600:.0f}小时{totaltime//60%60:.0f}分{totaltime%60:.1f}秒\n')
            f.write(f'实际互动观众数,{len(self.individual_users)}人\n')
            f.write(f'总弹幕数,{self.total_danmaku}条\n')
            f.write(f'平均弹幕数,{self.total_danmaku/(totaltime//60):.3f}条/分\n')
            f.write(f'总收益,{self.total_income:.1f}千金瓜子\n')
            f.write(f'平均收益,{self.total_income/(totaltime//60):.3f}千金瓜子/分\n')
            f.write(f'SuperChat收益,{self.total_income_sc:.1f}千金瓜子\n')
            f.write(f'礼物收益,{self.total_income_gift:.1f}千金瓜子\n')
            f.write(f'总上舰数,{self.total_guards}人\n')
            f.write(f'舰长,{self.total_guards_l3}人\n')
            f.write(f'提督,{self.total_guards_l2}人\n')
            f.write(f'总督,{self.total_guards_l1}人\n')
            f.write(f'最高人气值,{self.max_pop}\n')

    def stats_genreport_sensitive(self,filename):
        # Real time axis.
        rbasetime = dt.datetime.fromtimestamp(self.abstime_start//1000//60*60,tz=dt.timezone(dt.timedelta(hours=8)))
        rx=[rbasetime+dt.timedelta(seconds=i) for i in range(0,(self.max_trend_len)*self.resolution,self.resolution)]
        # Fake time axis starting from EPOCH time 0(UTC).
        basetime = dt.datetime.fromtimestamp(0,tz=dt.timezone.utc)
        x=[basetime+dt.timedelta(seconds=i) for i in range(0,(self.max_trend_len)*self.resolution,self.resolution)]
        y0=[0]*len(x)
        y2=np.array(self.trend_gift_paid)
        y3=np.array(self.trend_gift_free)
        y4=np.array(self.trend_sc)
        y5=np.array(self.trend_guard)

        # Plotting
        rcParams['font.family'] = "WenQuanYi Micro Hei"
        plt.figure(figsize=(21, 7), dpi=180)
        danmaku=plt.axes()
        danmaku.plot(x,y2,label='金瓜子')
        danmaku.plot(x,y3,label='银瓜子')
        danmaku.plot(x,y4,label='SuperChat')
        danmaku.plot(x,y5,label='舰长')
        danmaku.set_xlabel("时轴")
        danmaku.set_ylabel("千金瓜子")
        danmaku.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0,60,self.xtick_width)))
        danmaku.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
        danmaku.set_xlim(left=0,right=x[-1])
        danmaku.set_ylim(bottom=0)
        danmaku.legend(loc='upper left')
        danmaku.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=dt.timezone.utc))
        rtime=danmaku.twiny()
        rtime.set_xlim(left=rx[0],right=rx[-1])
        rtime.set_ylim(bottom=0)
        rtime.plot(rx,y0,c='white')
        rtime.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(self.abstime_start//1000//60%5,60,self.xtick_width)))
        rtime.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
        rtime.set_xlabel("时间")
        rtime.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=dt.timezone(dt.timedelta(hours=8))))
        plt.savefig(filename)

    def stats_genreport_public(self,filename):
        # Real time axis. Unused for now.
        rbasetime = dt.datetime.fromtimestamp(self.abstime_start//1000//60*60,tz=dt.timezone(dt.timedelta(hours=8)))
        rx=np.array([rbasetime+dt.timedelta(seconds=i) for i in range(0,(self.max_trend_len)*self.resolution,self.resolution)])
        # Fake time axis starting from EPOCH time 0(UTC).
        basetime = dt.datetime.fromtimestamp(0,tz=dt.timezone.utc)
        x=np.array([basetime+dt.timedelta(seconds=i) for i in range(0,(self.max_trend_len)*self.resolution,self.resolution)])
        y0=[0]*len(x)
        y1=np.array(self.trend_danmaku)
        y6=np.array(self.trend_pop)/self.trend_pop_count

        # Plotting
        rcParams['font.family'] = "WenQuanYi Micro Hei"
        plt.figure(figsize=(21, 7), dpi=180)
        danmaku=plt.axes()
        danmaku.plot(x,y1,'y',label='弹幕')
        danmaku.set_xlabel("时轴")
        danmaku.set_ylabel("弹幕（条/分）")
        danmaku.grid(True,which='major',axis='x',color='dimgray',linestyle='-')
        danmaku.grid(True,which='minor',axis='x',color='lightgray',linestyle='--')
        danmaku.grid(True,which='major',axis='y',color='lightgray',linestyle='--')
        danmaku.legend(loc='upper left')
        #danmaku.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=dt.timezone.utc))
        danmaku.xaxis.set_ticks([])
        income=danmaku.twinx()
        income.plot(x,y6,label='人气')
        income.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0,60,self.xtick_width)))
        income.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
        income.set_xlim(left=0,right=x[-1])
        income.set_ylim(bottom=0)
        income.set_ylabel("人气")
        income.legend(loc='upper right')
        income.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=dt.timezone.utc))
        # Recompute lower x axis labels. Not in use right now.
        #lastpivot_timestamp = rx[0]
        #for timestamp in self.timestamp_list[1:]:
        #    pivot = np.argmax(rx>dt.datetime.fromtimestamp(timestamp//1000,tz=dt.timezone(dt.timedelta(hours=8))))
        #    diff = dt.timedelta(seconds=86400)-(rx[pivot]-lastpivot_timestamp)
        #    x[pivot:] += diff
        #    lastpivot_timestamp = rx[pivot]
        rtime=income.twiny()
        rtime.set_xlim(left=rx[0],right=rx[-1])
        rtime.set_ylim(bottom=0)
        rtime.plot(rx,y0,c='white')
        rtime.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(self.abstime_start//1000//60%5,60,self.xtick_width)))
        rtime.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
        rtime.set_xlabel("时间")
        rtime.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=dt.timezone(dt.timedelta(hours=8))))
        plt.savefig(filename)

    def sortfiles(self,filelist):
        timestamps=[]
        for filename in filelist:
            with open(filename,'r') as f:
                record_match = self.stampreg.match(f.readline())
                timestamps.append(int(int(record_match.group(1))-float(record_match.group(3))*1000))
        return np.array(filelist)[np.argsort(timestamps)],np.sort(timestamps)

    def parse(self,filelist):
        # Return error on empty filelist
        if len(filelist)==0:
            print("Error: Please specify at least one file.")
            exit(-1)
        # Process as multiple files from same stream.
        if self.concatenate:
            filelist,self.timestamp_list = self.sortfiles(filelist)
            self.stats_init(self.timestamp_list[0])
            for filename in filelist:
                with open(filename,'r') as f:
                    records = f.readlines()
                for entry in records:
                    info = self.stampreg.match(entry)
                    if info.group(2)=='DANMAKU':
                        self.parse_danmaku(int(info.group(1)),info.group(3),entry[info.end():])
                    elif info.group(2)=='GIFT':
                        self.parse_gift(int(info.group(1)),info.group(3),entry[info.end():])
                    elif info.group(2)=='SUPERCHAT':
                        self.parse_sc(int(info.group(1)),info.group(3),entry[info.end():])
                    elif info.group(2)=='GUARD':
                        self.parse_guard(int(info.group(1)),info.group(3),entry[info.end():])
                    elif info.group(2)=='POP':
                        self.parse_pop(int(info.group(1)),info.group(3),entry[info.end():])
                    else:
                        print(f"Warning: Malformed LAR file with {info.group(2)} entry tag!\n")
            self.stats_wrapup()
            if self.report_generation_flag&1:
                self.stats_genreport_public(re.sub(r'.lar$','.clipguide.png',filelist[0]))
            if self.report_generation_flag&2:
                self.stats_genreport_sensitive(re.sub(r'.lar$','.sensitive.png',filelist[0]))
            if self.report_generation_flag&4:
                self.stats_genreport_text(re.sub(r'.lar$','.sensitive.txt',filelist[0]))
            exit(0)
        # Process as seperate files
        for filename in filelist:
            if not os.path.isfile(filename):
                print(f"Error: File {filename} not found. Skipping...\n")
                continue
            with open(filename,'r') as f:
                records = f.readlines()
            if len(records)<=1:
                print(f"Error: File {filename} has 0 timespan. Skipping...\n")
                continue
            first_record_match = self.stampreg.match(records[0])
            self.timestamp_list = [int(int(first_record_match.group(1))-float(first_record_match.group(3))*1000)]
            self.stats_init(self.timestamp_list[0])
            for entry in records:
                info = self.stampreg.match(entry)
                if info.group(2)=='DANMAKU':
                    self.parse_danmaku(int(info.group(1)),info.group(3),entry[info.end():])
                elif info.group(2)=='GIFT':
                    self.parse_gift(int(info.group(1)),info.group(3),entry[info.end():])
                elif info.group(2)=='SUPERCHAT':
                    self.parse_sc(int(info.group(1)),info.group(3),entry[info.end():])
                elif info.group(2)=='GUARD':
                    self.parse_guard(int(info.group(1)),info.group(3),entry[info.end():])
                elif info.group(2)=='POP':
                    self.parse_pop(int(info.group(1)),info.group(3),entry[info.end():])
                else:
                    print(f"Warning: Malformed LAR file with {info.group(2)} entry tag!\n")
            self.stats_wrapup()
            if self.report_generation_flag&1:
                self.stats_genreport_public(re.sub(r'.lar$','.clipguide.png',filename))
            if self.report_generation_flag&2:
                self.stats_genreport_sensitive(re.sub(r'.lar$','.sensitive.png',filename))
            if self.report_generation_flag&4:
                self.stats_genreport_text(re.sub(r'.lar$','.sensitive.txt',filename))

    def parse_danmaku(self,timestamp,meta,danmaku):
        meta = [float(i) for i in meta.split(',')]
        dminfo = self.danreg.match(danmaku)
        userinfo = self.smartcomma.split(dminfo.group(1))
        badgeinfo = self.smartcomma.split(dminfo.group(2))
        content = dminfo.group(3)
        # Counting danmaku to the statistics
        edata = BiliDanmaku(timestamp,*meta,*userinfo,*badgeinfo,content)
        self.reltime = max(self.reltime,edata.time_rel)
        self.abstime = max(self.abstime,edata.time_abs)
        self.total_danmaku += 1
        if edata.uid not in self.individual_users:
            self.individual_users.append(edata.uid)
        self.cache_danmaku.append(edata)
        #while len(self.trend_danmaku)*self.resolution<self.reltime:
        while len(self.trend_danmaku)*self.resolution<(self.abstime-self.abstime_start)/1000:
            self.trend_danmaku.append(0)
        #self.trend_danmaku[int(edata.time_rel)//self.resolution] += 1
        self.trend_danmaku[(edata.time_abs-self.abstime_start)//1000//self.resolution] += 1

    def parse_gift(self,timestamp,meta,gift):
        meta = [int(i) if i.isdigit() else i for i in meta.split(',')]
        meta[0] = float(meta[0])
        giftinfo = self.giftreg.match(gift)
        userinfo = self.smartcomma.split(giftinfo.group(1))
        content = self.smartcomma.split(giftinfo.group(2))
        content[1] = int(content[1])
        # Counting gift to the statistics
        edata = BiliGift(timestamp,*meta,*userinfo,*content)
        self.reltime = max(self.reltime,edata.time_rel)
        self.abstime = max(self.abstime,edata.time_abs)
        if edata.uid not in self.individual_users:
            self.individual_users.append(edata.uid)
        if edata.gift_coin_type == 'silver' or edata.gift_price == 0:
            self.cache_gift_free.append(edata)
            while len(self.trend_gift_free)*self.resolution<(self.abstime-self.abstime_start)/1000:
                self.trend_gift_free.append(0)
            self.trend_gift_free[(edata.time_abs-self.abstime_start)//1000//self.resolution] += edata.gift_coin_count/1000
        else:
            self.cache_gift_paid.append(edata)
            self.total_income += edata.gift_coin_count/1000
            self.total_income_gift += edata.gift_coin_count/1000
            while len(self.trend_gift_paid)*self.resolution<(self.abstime-self.abstime_start)/1000:
                self.trend_gift_paid.append(0)
            self.trend_gift_paid[(edata.time_abs-self.abstime_start)//1000//self.resolution] += edata.gift_coin_count/1000

    def parse_sc(self,timestamp,meta,superchat):
        meta = [int(i) if i.isdigit() else i for i in meta.split(',')]
        meta[0] = float(meta[0])
        SCinfo = self.giftreg.match(superchat)
        userinfo = self.smartcomma.split(SCinfo.group(1))
        content = SCinfo.group(2)
        # Counting SC to the statistics
        edata = BiliSC(timestamp,*meta,*userinfo,content)
        self.reltime = max(self.reltime,edata.time_rel)
        self.abstime = max(self.abstime,edata.time_abs)
        if edata.uid not in self.individual_users:
            self.individual_users.append(edata.uid)
        self.total_income += edata.SC_price
        self.total_income_sc += edata.SC_price
        self.cache_sc.append(edata)
        while len(self.trend_sc)*self.resolution<(self.abstime-self.abstime_start)/1000:
            self.trend_sc.append(0)
        self.trend_sc[(edata.time_abs-self.abstime_start)//1000//self.resolution] += edata.SC_price

    def parse_guard(self,timestamp,meta,guard):
        meta = [int(i) if i.isdigit() else i for i in meta.split(',')]
        meta[0] = float(meta[0])
        guardinfo = self.giftreg.match(guard)
        userinfo = self.smartcomma.split(guardinfo.group(1))
        content = [int(i) for i in self.smartcomma.split(guardinfo.group(2))]
        # Counting new guard to the statistics
        edata = BiliGuard(timestamp,*meta,*userinfo,*content)
        self.reltime = max(self.reltime,edata.time_rel)
        self.abstime = max(self.abstime,edata.time_abs)
        if edata.uid not in self.individual_users:
            self.individual_users.append(edata.uid)
        self.total_guards += 1
        if edata.guard==3:
            self.total_guards_l3 += 1
        elif edata.guard==2:
            self.total_guards_l2 += 1
        elif edata.guard==1:
            self.total_guards_l1 += 1
        self.cache_guard.append(edata)
        while len(self.trend_guard)*self.resolution<(self.abstime-self.abstime_start)/1000:
            self.trend_guard.append(0)
        self.trend_guard[(edata.time_abs-self.abstime_start)//1000//self.resolution] += edata.gift_price/1000

    def parse_pop(self,timestamp,meta,popularity):
        meta = float(meta)
        popularity = int(popularity)
        # Non dedicated data structure for popularity update. Using (timestamp,time, popularity) tuple instead.
        # Counting popularity info to the statistics
        self.reltime = max(self.reltime,meta)
        self.abstime = max(self.abstime,timestamp)
        self.max_pop = max(self.max_pop,popularity)
        self.cache_pop.append((timestamp,meta,popularity))
        while len(self.trend_pop)*self.resolution<(self.abstime-self.abstime_start)/1000:
            self.trend_pop.append(0)
            self.trend_pop_count.append(0)
        self.trend_pop[(timestamp-self.abstime_start)//1000//self.resolution] += popularity
        self.trend_pop_count[(timestamp-self.abstime_start)//1000//self.resolution] += 1

if __name__=='__main__':
    pr = LARParse()
    i = 0
    while True:
        i+=1
        if sys.argv[i]=='public':
            pr.report_generation_flag |= 1
        elif sys.argv[i]=='sensitive':
            pr.report_generation_flag |= 2
        elif sys.argv[i]=='text':
            pr.report_generation_flag |= 4
        elif sys.argv[i]=='concatenate':
            pr.concatenate = True
        else:
            break
    if not pr.report_generation_flag:
        pr.report_generation_flag = 1
    pr.parse(sys.argv[i:])
