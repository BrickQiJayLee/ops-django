#!/usr/bin/env python
#-*- coding:utf8 -*-

import commands

def cmd(cmdStr):
    status, out = commands.getstatusoutput(cmdStr)
    if status != 0 :
        print "[%s] ERROR:%s"%(cmdStr, out)
        return 1
    else:
        return out