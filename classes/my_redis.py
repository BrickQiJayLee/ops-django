#-*- coding:utf8 -*-

import sys
sys.path.append("..")
import my_redis
from classes import config

def redis_handler(config_section, db):
    c = config.config("config_db.ini")
    ip = c.getOption(config_section, "ip")
    password = c.getOption(config_section, "password")
    port = c.getOption(config_section, "port")
    r = my_redis.Redis(host=ip, password=password, port=port, db=db)
    return r