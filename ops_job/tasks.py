# coding=utf-8
from __future__ import absolute_import
import django
django.setup()
import logging
from celery import shared_task
import json
import traceback
from ops_job.views.script_executor import get_job_name, get_history_id, exec_scripts

_logger = logging.getLogger("ops_scripts")


@shared_task()
def celery_scripts(*args, **kwargs):
    '''
    执行脚本的celery方法
    :return:
    '''
    try:
        import urllib, urllib2
        script_job_name = get_job_name(kwargs.get('script_name'))
        celery_kwargs = {
            "args_type": 'file' if kwargs['args_type'] == '2' else 'normal',
            "script_job_name": script_job_name,
            "is_root": kwargs['is_root'],
            "script_args": kwargs['script_args'],
            "module_args": kwargs['module_args'],
            "history_id": get_history_id(script_job_name)    #创建任务
        }
        http_args = {
            'kwargs': json.dumps(celery_kwargs)
        }
        # 执行任务
        script_urlencode = urllib.urlencode(http_args)
        requrl = "http://127.0.0.1:8000/ops_job/script/script_http"
        req = urllib2.Request(url=requrl, data=script_urlencode)
        res_data = urllib2.urlopen(req)
        ret = json.loads(res_data.read())
        if ret.get('result', None) == 'failed':
            _logger.info("Script celery 500 error, %s" % ret['result'])
        elif ret.get('result', None) == 'success':
            if ret['data']['host_failed'] or ret['data']['host_unreachable']:
                failed_ip = list()
                if ret['data']['host_failed']:
                    failed_ip += ret['data']['host_failed'].keys()
                if ret['data']['host_unreachable']:
                    failed_ip += ret['data']['host_unreachable'].keys()
                if failed_ip:
                    failed_ips = ','.join(failed_ip)
                else:
                    failed_ips = 'no ip'
                _logger.info("Script celery Ansible Failed IP: %s" % failed_ips)
                try:
                    _logger.info("failed_info: %s" % json.dumps(ret))
                except(Exception):
                    _logger.error("Send Failed IP failed : %s" % traceback.format_exc())
    except Exception:
        _logger.error("task execute failed, %s" % traceback.format_exc())
        pass