# bilibili-live-recorder

Forked from [zachMelody/bilibili-live-recorder](https://github.com/zachMelody/bilibili-live-recorder).

[B站](https://ilibili.com)直播录播姬。支持在未开播时监听房间，并在开播时自动开始录制。支持源视频流录制，弹幕录制。支持使用cookies。支持使用[Server酱](http://sc.ftqq.com)提醒直播开始。支持多房间同时监听/录制，并且每个房间的录制设定可以独立进行配置。

从[zachMelody/bilibili-live-recorder](https://github.com/zachMelody/bilibili-live-recorder)fork而来。重写了主程序`run.py`，添加了弹幕录制和使用cookies的功能，并且移除了python配置文件，改用json格式的配置文件。

## 用法/Usage:

### 运行程序:
```
python run.py [-c <CONFIG_FILE>]
```
默认情况下会尝试读取同目录下的`config.json`作为配置文件。使用`-c`以读取指定的配置文件。

### 配置文件设置:
基本的配置格式可直接参考`config.json`中的样例。Root下有两个object，分别是`default`和`rooms`。`default`中的设置是每个房间的默认录制设定，如果没有对房间作额外设定，就会使用这些设置。具体可以配置的设置如下:
| Object | Type | Explanation | 
|--------|------|-------|
|`enable_inform`| boolean | 是否使用[Server酱](http://sc.ftqq.com)推送通知直播开始。详细用法见其网站。 |
|`inform_url`| string | 填入[Server酱](http://sc.ftqq.com)的通知地址。获取方法同样见其网站。 |
|`check_interval`| integer | 每隔多少时间查询一次房间的开播状态。（单位：秒）</br>（这也决定了最坏情况下会错过多长的直播开头，但不建议设置短于60秒，以免在开播时影响录制进程。） |
|`saving_path`| string | 录像及弹幕的保存路径，相对或绝对路径均可。 |
|`use_cookies`| boolean | 是否使用cookies文件。详见下文。 |
|`cookies_file`| string | 若使用cookies文件，填入cookies文件的路径。 |
|`capture_danmaku`| boolean | 是否录制弹幕。 |

注意，不使用的设置可以填空字符串`""`，但不要从配置文件里删除这项设置。

`rooms`是一个`list`，罗列每个你想要监听/录制的房间。每个房间需设置房间号:
| Object | Type | Explanation | 
|--------|------|-------|
|`room_id  `| integer | (必填)直播间号，短号或原房间号均可。 |

除此之外，`default`中的设置均可选填，以对不同房间做不同设置。没有填的设置会自动使用`default`中的值。

### 关于cookies:
cookies的作用是保留登录信息。简单解释，不使用cookies录制就类似于不登录B站帐号的情况下直接看直播，而使用了就相当于登录了。

一般情况下，录制直播是不需要cookies的。目前B站对路人观看直播的画质没有限制。同时，即使用了cookies，这个程序也不会帮你领瓜子或者赚小心心。所以一般使用的话不必费心，使用设置为`false`，然后路径留空即可。

不过有一个例外。B站最近开始有付费收看的直播了，比如某vup的粉丝见面会和某vup的演唱会。这种情况下就需要cookies了，否则获取不到直播地址。

关于如何从浏览器中获得你的登录cookies并保存为txt文件，请自行谷歌/百度。chrome用户可以去扩展商店搜索cookies，有一些很方便的插件可以一键导出/复制cookies。

### 关于弹幕录制及其格式:

使用了[blivedm](https://github.com/yu17/blivedm)连接B站直播弹幕的websocket接口。

录制弹幕的最终目的是能够在离线状态播放的同时显示弹幕。出于这一考虑，弹幕的保存格式与B站一般视频的弹幕XML文件格式基本兼容。换言之，你可以用[m13253/danmaku2ass](https://github.com/m13253/danmaku2ass)或其他类似工具将录制下来的弹幕转换为`ass`格式的字幕，这样播放时直接载入该字幕，就能实现有弹幕的直播回放。

目前仅完全支持普通弹幕（滚动/顶部/底部，彩色），部分支持SC（显示发送人、金额、弹幕内容，但显示时间与一般的顶部弹幕相同），不支持送礼等其他特殊事件。这是受限于[m13253/danmaku2ass](https://github.com/m13253/danmaku2ass)的功能，因此短时间不太能改进。未来可能考虑fork一下[danmaku2ass](https://github.com/yu17/danmaku2ass)，以添加直播特殊弹幕的支持。