# coding:utf-8
#!/usr/bin/env python


from classes import config
import traceback

def get_show_type():
    try:
        c = config.config("ip_type.ini")
        #c.getOption('SHOWTYPE', 'ipshowtype')
        return  str(c.getOption('SHOWTYPE', 'ipshowtype'))
    except Exception:
        print("Env_type get error： %s" % traceback.format_exc())
        return 'outer_ip'