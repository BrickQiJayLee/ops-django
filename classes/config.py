#!/usr/bin/env python
#-*- coding:utf8 -*-

import ConfigParser,os,re,io

class config:
    def __init__(self, filename):
        self.config = ConfigParser.RawConfigParser(allow_no_value=True)
        dir = os.path.dirname(os.path.abspath(__file__))
        path = "%s/../conf/" % dir
        filepath = path + filename
        if not os.path.exists(filepath):
            raise Exception("ERROR: %s该配置文件不存在！"%filepath)
        f = open(filepath)
        content = f.read()
        self.config.readfp(io.BytesIO(str(content)))
        f.close()

    def checkArg(self, str,info):
        '''检查参数是否为空'''
        if check.nullCheck(str) :
            raise Exception(info)

    def checkSection(self, section):
        '''检查配置文件的section是否存在'''
        if not self.config.has_section(section):
            raise Exception("没有%s该section"%section)

    def getOption(self,section,option,type="str",default=None):
        '''检查配置文件的option是否存在'''
        returnStr = ""
        if not self.config.has_option(section,option):
            #如果对应section中没有找到option则到通用的section中查找option
            if not self.config.has_option("common",option):
                if default != None:
                    return default
                else:
                    raise Exception("没有%s该option"%option)
                #return None
            else:
                if type == "bool":
                    returnStr = self.config.getboolean("common",option)
                elif type == "int":
                    returnStr = self.config.getint("common",option)
                elif type == "float":
                    returnStr = self.config.getfloat("common",option)
                else:
                    returnStr = self.config.get("common",option)
        else:
            if type == "bool":
                returnStr = self.config.getboolean(section,option)
            elif type == "int":
                returnStr = self.config.getint(section,option)
            elif type == "float":
                returnStr = self.config.getfloat(section,option)
            else:
                returnStr = self.config.get(section,option)
        return returnStr


