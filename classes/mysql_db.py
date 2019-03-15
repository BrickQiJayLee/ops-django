# coding=utf-8
import sys

sys.path.append("..")
from classes import config
import MySQLdb
# from DBUtils.PooledDB import PooledDB
import logging
import traceback


logger = logging.getLogger(__name__)

def dict_fetch_all(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
        ]


def change_query_data_tostring(query_data):
    '''
    将数据库取出来的数据转化为字符，因为datetime不支持json
    :param query_data:
    :return:
    '''
    for data in query_data:
        keys = data.keys()
        try:
            for key in keys:
                try:
                    if "blob" in key:
                        data.pop(key)
                    else:
                        data[key] = str(data[key]).encode("utf-8")
                except:
                    data.pop(key)
        except:
            pass
    return query_data


class conn_db:
    __pool = {}
    def __init__(self, db, config_section):
        """
        数据库构造函数，从连接池中取出连接，并生成操作游标
        """
        try:
            c = config.config("../conf/mysql.ini")
            user = c.getOption(config_section, "username")
            pwd = c.getOption(config_section, "password")
            host = c.getOption(config_section, "host")
            port = c.getOption(config_section, "port", "int")
            self.connect = self.db = MySQLdb.connect(host=host, user=user, passwd=pwd, db=db, port=port, charset='utf8')
        except Exception, e:
            print traceback.format_exc()
            #logger.error("connect database error - %s" % str(e))
            return

    def execute(self, sql, param=()):
        try:
            cursor1 = self.connect.cursor()
            index = cursor1.execute(sql, param)
            self.connect.commit()
            cursor1.close()
            return index
        except Exception, e:
            print traceback.format_exc()
            self.connect.rollback()
            #logger.error("execute sql error - %s" % str(e))
            return -1

    def execute_returnid(self, sql, param=()):
        try:
            cursor1 = self.connect.cursor()
            cursor1.execute(sql, param)
            self.connect.commit()
            index = int(cursor1.lastrowid)
            return index
        except Exception, e:
            self.connect.rollback()
            print traceback.format_exc()
            self.connect.rollback()
            #logger.error("execute sql error - %s" % str(e))
            return -1

    def executemany(self, sql, param=()):
        try:
            cursor1 = self.connect.cursor()
            index = cursor1.executemany(sql, param)
            self.connect.commit()
            cursor1.close()
            return index
        except Exception, e:
            print traceback.format_exc()
            self.connect.rollback()
            #logger.error("execute sql error - %s" % str(e))
            return -1

    def select(self, sql, param=()):
        try:
            cursor1 = self.connect.cursor()
            cursor1.execute(sql, param)
            self.connect.commit()
            get_data = dict_fetch_all(cursor1)
            cursor1.close()
            return get_data
        except Exception, e:
            print traceback.format_exc()
            #logger.error("execute sql error - %s" % str(e))
            return -1

    def close(self):
        self.connect.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connect.close()
