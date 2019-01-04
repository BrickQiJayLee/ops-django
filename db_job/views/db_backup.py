# coding=utf-8

# Create your views here.

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from classes import ansible_api, my_concurrent, crypto, mysql_db, config
import logging
import traceback
from db_job.models import DbJobDbInstance, DbJobDbBackupHistory
import json
from ops_django.settings import RUN_MODE
import time
from operator import itemgetter

_logger = logging.getLogger(__name__)

def datefield_to_str(date_data):
    '''
    mysql date格式转换为字符串格式
    :param date_data:
    :return:
    '''
    for i in date_data:
        if i.has_key("create_time") and i.get('create_time', None) is not None:
            i["create_time"] = i["create_time"].strftime("%Y-%m-%d %H:%M:%S")
        if i.has_key("update_time") and i.get('update_time', None) is not None:
            i["update_time"] = i["update_time"].strftime("%Y-%m-%d %H:%M:%S")
        if i.has_key("dtEventTime") and i.get('dtEventTime', None) is not None:
            i["dtEventTime"] = i["dtEventTime"].strftime("%Y-%m-%d %H:%M:%S")
    return date_data

#####################数据库备份#####################
@csrf_exempt
#@login_required(login_url='/login/user_login')
def backup_excute_page(request):
    '''
    数据库备份页面
    :param request:
    :return:
    '''
    all_db_resource = list(DbJobDbInstance.objects.all().values())
    db_instances = {}
    for i in all_db_resource:
        db_instances[i['db_mark']] = i
    #db_info = [ i for i in all_db_resource]
    db_marks = [ i['db_mark'] for i in all_db_resource]
    #print db_marks
    return HttpResponse(json.dumps({"result": "success", "data": {"db_info": db_instances, "db_marks": db_marks}}))



def get_mysql_container_name_and_passwd(db_instance):
    '''
    获取mysql密码和container name
    :return:
    '''
    db_resource = DbJobDbInstance.objects.filter(db_mark=db_instance).values()
    if not len(db_resource) == 1:
        return False, '', '', ''
    else:
        return True, db_resource[0]['db_container_name'], db_resource[0]['db_user_name'], db_resource[0]['db_passwd'], db_resource[0]['id']


def db_backup_job(job_list, db_ip_port):
    '''
    执行db备份方法
    :return:
    '''
    try:
        db_ip = db_ip_port.strip().split(':')[0]
        db_port = db_ip_port.strip().split(':')[1]
        if job_list['db'] is None or job_list['table'] is None:
            return json.dumps({"result": "failed", "info": "%s db or table is none" % db_ip_port})
        else:
            print job_list
            db_instance_id = job_list['db_instance_id']
            db_instance_name = job_list['db_mark']
            db_container_name = job_list['db_container_name_slave'] if job_list['db_container_name_slave'] else\
                job_list['db_container_name']
            db_service_type = job_list['db_service_type']
            db_passwd = crypto.passwd_deaes(job_list['db_passwd'])
            db_user_name = job_list['db_user_name']
            db = job_list['db']
            table = job_list['table']
            ansible_interface = ansible_api.AnsiInterface(become=True, become_method='sudo', become_user='root')
            time_now = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
            # mk backup dir
            ansible_interface.make_dir(db_ip, '/data/mysqlbackup/ state=directory')
            ansible_interface.make_dir(db_ip, '/data/mysqlbackup/%s state=directory' % db_instance_name)
            ansible_interface.make_dir(db_ip, '/data/mysqlbackup/%s/%s_%s state=directory' % (db_instance_name, db, table))

            if db_service_type == 'container':
                cmd = "docker exec %s  bash -c 'mysqldump -h127.0.0.1 " \
                      "-u%s -P%s -p%s --opt --skip-lock-tables %s %s' > /data/mysqlbackup/%s/%s_%s/%s.sql" \
                      % (db_container_name, db_user_name, db_port, db_passwd, db, table, db_instance_name,
                         db, table, time_now)
            elif db_service_type == 'service':
                cmd = "mysqldump -h127.0.0.1 " \
                      "-u%s -P%s -p%s --opt --skip-lock-tables %s %s > /data/mysqlbackup/%s/%s_%s/%s.sql" \
                      % (db_user_name, db_port, db_passwd, db, table, db_instance_name,
                         db, table, time_now)
            else:
                return json.dumps({"result": "failed","info": u"没有该服务类型对应命令"})

            # do backup
            result = ansible_interface.exec_shell(db_ip, cmd)

            # parse result
            if result['host_failed']:
                _ret = {"result": "failed", "info": "ip: %s, db: %s, failed_info: %s" % (db_ip, db, result['host_failed'][db_ip]['stderr'])}  # 执行结果放入Queue
            elif result['host_unreachable']:
                _ret = {"result": "failed", "info": " ip: %s, ureachable: %s" % (db_ip, result['host_unreachable'])}  # 执行结果放入Queue
            else:
                ok_ip = result['host_ok'].keys()
                _ret = {"result": "success", "info": "ip: %s, backup_file: %s" % (','.join(ok_ip), "/data/mysqlbackup/%s/%s_%s/%s.sql" % (db_instance_name,
                         db, table, time_now))}
                dteventtime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
                data = [(
                    dteventtime,
                    db_instance_id,
                    db,
                    table,
                    "/data/mysqlbackup/%s/%s_%s/%s.sql" % (db_instance_name, db, table, time_now)
                )]
                c = config.config('mysql.ini')
                db_name = c.getOption(RUN_MODE, 'dbname')
                with mysql_db.conn_dbpool(db_name, RUN_MODE) as _db:
                    sql = "insert into db_job_db_backup_history (`dtEventTime`,`db_instance_id`,`dbs`,`tables`,`result`) values (%s,%s,%s,%s,%s)"
                    _db.executemany(sql, data)
                return json.dumps(_ret)
            return json.dumps(_ret)
    except Exception:
        try:
            table = job_list.get('table', 'None')
            db = job_list.get('db', 'None')
            db_ip = db_ip_port.strip().split(':')[0]
        except:
            table = 'None'
            db = 'None'
            db_ip = 'None'
        _logger.error(traceback.format_exc())
        return json.dumps({"result": "failed", "info": "ip: %s, db: %s,table: %s, failed_info: %s" % (db_ip, db, table, traceback.format_exc())})


#@login_required(login_url='/login/user_login')
@csrf_exempt
def db_backup_start(request):
    try:
        db_instance = request.POST.get('db_instance', None)
        dbs = request.POST.get('dbs', None)
        tables = request.POST.get('tables', None)
        selectdb = json.loads(request.POST.get('selectdb', None))
        if selectdb['db_slave'] == '' or selectdb['db_slave'] is None:
            db_ip_port = selectdb['db_master']
        else:
            db_ip_port = selectdb['db_slave']
        if None in [db_instance, dbs, tables]:
            return HttpResponse(json.dumps({"result": "failed", "info": "DB信息有误，请对比注册表"}))
        backup_list = []
        for db in list(set(dbs.strip().split("\n"))):
            for table in list(set(tables.strip().split('\n'))):
                backup_list.append({'db':db.strip(), 'table': table.strip()})
        # 解开dbinstance信息
        for item in backup_list:
            item['db_instance_id'] = selectdb['id']
            item['db_instance_name'] = selectdb['db_mark']
            item['db_product'] = selectdb['db_product']
            item['db_service_name_slave'] = selectdb['db_service_name_slave']
            item['db_container_name'] = selectdb['db_container_name']
            item['db_mark'] = selectdb['db_mark']
            item['db_service_type'] = selectdb['db_service_type']
            item['db_master'] = selectdb['db_master']
            item['db_env'] = selectdb['db_env']
            item['db_passwd'] = selectdb['db_passwd']
            item['db_service_name'] = selectdb['db_service_name']
            item['db_product_id'] = selectdb['db_product_id']
            item['db_slave'] = selectdb['db_slave']
            item['db_container_name_slave'] = selectdb['db_container_name_slave']
            item['db_user_name'] = selectdb['db_user_name']
        # 开始并发处理
        db_backup_multi_process = my_concurrent.MyMultiProcess(10)
        for i in backup_list:
            db_backup_multi_process.multi_process_add(db_backup_job, i, db_ip_port)
        db_backup_multi_process.multi_process_wait()  # 等待执行完成
        result = db_backup_multi_process.get_result()

        g_res = {"failed":[], "success": []}
        for _res in result:
            __res = json.loads(_res.get())
            if __res['result'] == "failed":
                g_res["failed"].append(__res['info'])
            elif __res['result'] == "success":
                g_res["success"].append(__res['info'])
        if g_res["failed"]:
            return HttpResponse(json.dumps({"result": "failed", "data": g_res}))
        return HttpResponse(json.dumps({"result": "success", "data": g_res}))
    except Exception:
        _logger.error(traceback.format_exc())
        g_res = "500 内部错误 %s"%traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "data": g_res}))

#####################数据库备份历史#####################
@csrf_exempt
def show_db_backup_history(request):
    all_history = list(DbJobDbBackupHistory.objects.exclude(dtEventTime=None).values())
    all_history_by_time = sorted(all_history, key=itemgetter('dtEventTime'))
    all_history_by_time.reverse()
    for i in all_history_by_time:
        instance_name = DbJobDbInstance.objects.filter(id=i['db_instance_id']).values()
        if len(instance_name) == 0:
            i['instance_name'] = ''
        else:
            i['instance_name'] = instance_name[0]['db_mark']
    all_history_by_time = datefield_to_str(all_history_by_time)
    time_now = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    last_week = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*60*60))
    last_month = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*60*60*30))
    date_filter = [
        {"text": str(time_now), "value": str(time_now)},
        {"text": str(last_week), "value": str(last_week)},
        {"text": str(last_month), "value": str(last_month)},
    ]
    print date_filter
    return HttpResponse(json.dumps({"result": "success","data":all_history_by_time, "date_filter": date_filter}))