# coding=utf-8


# python2适用

import threading
from pathos import multiprocessing

def div_list(ls,n):
    '''
    尽量平分列表
    :param ls:
        ls - 传入的列表对象
        n - 需要划分为多少个子列表
    :param n:
    :return:
    '''
    if not isinstance(ls,list) or not isinstance(n,int):
        print("not list")
        raise AttributeError
    ls_len = len(ls)
    if n<=0 or ls_len==0:
        print("num is wrong or list is empty")
        raise AttributeError
    elif n >= ls_len:
        return [[i] for i in ls]
    else:
        j = ls_len/n
        k = ls_len%n
        ### j,j,j,...(前面有n-1个j),j+k
        #步长j,次数n-1
        ls_return = []
        for i in xrange(0,(n-1)*j,j):
            ls_return.append(ls[i:i+j])
        #算上末尾的j+k
        ls_return.append(ls[(n-1)*j:])
        return ls_return

# 多线程
class MyMultiThread():
    def __init__(self):
        self.runlist = list()

    def multi_thread_Add(self, func, name, *args, **kwargs):
        t = threading.Thread(target=func, name=name, args=args, kwargs=kwargs)
        self.runlist.append(t)

    def multi_thread_start(self):
        for t in self.runlist:
            t.start()

    def multi_thread_wait(self):
        for t in self.runlist:
            t.join()


# 多进程
class MyMultiProcess():
    '''
    django数据库操作不能使用,与父进程冲突，应该使用subprocess
    '''
    def __init__(self, processes):
        self._pool = multiprocessing.Pool(processes=processes)
        self.result = list()

    def multi_process_add(self, func, *args, **kwargs):
        self.result.append(self._pool.apply_async(func, args=args, kwds=kwargs))

    def multi_process_wait(self):
        self._pool.close()
        self._pool.join()

    def get_result(self):
        return self.result

