# coding=utf-8

import signal
import logging

_logger = logging.getLogger(__name__)

def callback():
    print "kprocess time out error"

class TimeOutException(Exception):
    pass

def setTimeout(num, callback=callback):
    def wraper(func):
        def handle(signum, frame):
            raise TimeOutException("multiprocess out of time: %ss！" % num)

        def toDo(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, handle)
                signal.alarm(num)  # 开启闹钟信号
                rs = func(*args, **kwargs)
                signal.alarm(0)  # 关闭闹钟信号
                return rs
            except TimeOutException, e:
                callback()

        return toDo
    return wraper