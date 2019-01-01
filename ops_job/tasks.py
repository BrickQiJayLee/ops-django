# coding=utf-8
from __future__ import absolute_import
import django
django.setup()
import logging
from celery import shared_task
import json
import traceback
from classes.my_cmd import cmd

_logger = logging.getLogger("ops_scripts")

@shared_task()
def ops_job_monitor():
    '''
    注册服务监控
    :return:
    '''
    import urllib2
    url = 'http://127.0.0.1:8000/ops_job/script/monitor'
    req = urllib2.Request(url=url)
    res = urllib2.urlopen(req)
    ret = json.loads(res.read())
    if ret.get('result', None) == 'failed':
        _logger.info("ops_job_monitor celery 500 error, %s" % ret['result'])
    elif ret.get('result', None) == 'success':
        if ret['info']['host_unreachable']:
            unreachable_ip = [','.join(i.keys()) for i in ret['info']['host_unreachable']]
            _logger.info("unreachable_ip: %s" % unreachable_ip)
        if ret['info']['host_failed']:
            failed_ip = [','.join(i.keys()) for i in ret['info']['host_failed']]
            _logger.info("failed_ip: %s" % failed_ip)


@shared_task()
def tz_scrpits(*args, **kwargs):
    '''
    执行脚本的celery方法
    :return:
    '''
    import urllib
    import urllib2
    http_args = {
        'kwargs': json.dumps(kwargs)
    }
    script_urlencode = urllib.urlencode(http_args)
    requrl = "http://127.0.0.1:8000/ops_job/script/script_http"
    req = urllib2.Request(url=requrl, data=script_urlencode)
    res_data = urllib2.urlopen(req)
    ret = json.loads(res_data.read())
    if ret.get('result', None) == 'failed':
        _logger.info("Script celery 500 error, %s" % ret['result'])
    elif ret.get('result', None) == 'success':
        if ret['info']['host_failed'] or ret['info']['host_unreachable']:
            failed_ip = list()
            if ret['info']['host_failed']:
                failed_ip += ret['info']['host_failed'].keys()
            if ret['info']['host_unreachable']:
                failed_ip += ret['info']['host_unreachable'].keys()
            if failed_ip:
                failed_ips = ','.join(failed_ip)
            else:
                failed_ips = 'no ip'
            _logger.info("Script celery Ansible Failed IP: %s" % failed_ips)
            try:
                _logger.info("failed_info: %s" % json.dumps(ret))
            except(Exception):
                _logger.error("Send Failed IP failed : %s" % traceback.format_exc())