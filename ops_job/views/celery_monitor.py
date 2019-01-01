# coding=utf-8

# Create your views here.
from __future__ import absolute_import
from django.http import HttpResponse
import traceback
import json
import os
import logging
from django.db.models import Q
from classes import ansible_api, my_concurrent
from cmdb.models import CmdbTreeNode
from cmdb.views.tree import get_ip_by_name

_logger = logging.getLogger(__name__)

def get_service_info():
    service_info = list(CmdbTreeNode.objects.exclude(service_info=None).filter(~Q(service_info='')).values())
    return service_info

def _service_monitor(_monitor):
    try:
        ip = _monitor.get('ip', None)
        services = _monitor['services']
        actions = list()
        monitor_types = {}
        for _service in services:  #分类所有告警类型
            service_type = _service.get('service_type',None)
            if not monitor_types.has_key(service_type):
                monitor_types[service_type] = list()
            monitor_types[service_type].append("%s:%s" % (_service.get('service', None), _service.get('port', None)))
        for m_type, m_list in monitor_types.items():   #定义告警类型执行的脚本
            script = "ops_job/script/%s_monitor.sh" % m_type
            if not os.path.exists(script):
                script = "ops_job/script/%s_monitor.py" % m_type
            service_names = m_list
            #print service_name
            if not os.path.exists(script) or len(script) == 0:
                failed_info = {
                    'host_ok': '',
                    'host_unreachable': '',
                    'host_failed': {ip: {"msg": "ansible exec failed", "trace_back":"service type is wrong or service name is None "}}
                }
                _logger.error("monitor failed:  %s" % failed_info)
            else:
                actions.append(dict(action=dict(module='script', args="%s '%s'" % (script, ','.join(service_names)))))
        ansible_play = ansible_api.AnsibleApi(name="Ansible Celery Monitor", hosts=ip, actions=actions, become=True, become_method='sudo', become_user='root')
        ansible_play._run_task()
        result = ansible_play._get_result()
        return json.dumps(result)
        #result_q.put(result)    #执行结果放入Queue
    except Exception:
        ip = _monitor.get('ip', None)
        _logger.error("monitor failed:  %s" % traceback.format_exc())
        return json.dumps({
            'host_ok': '',
            'host_unreachable': '',
            'host_failed': {ip: {"msg": "ansible exec failed", "trace_back": traceback.format_exc()}}
        })


def service_monitor(request):
    try:
        service_info = get_service_info()
        _monitors = list()  #监控任务
        __monitor = dict()
        for services in service_info:
            _services = services['service_info'].split(';')
            node_name = services['node_name']
            ips = get_ip_by_name(node_name)
            if not len(ips) == 0:
                for ip in ips:
                    if ip not in __monitor.keys():
                        __monitor[ip] = {
                                "services":[
                                ]
                            }
                    for _service in _services:
                        if len(_service.split('@')[1].split(':')) == 2:
                            port = _service.split('@')[1].split(':')[1]
                        else:
                            port = ''
                        __monitor[ip]['services'].append({
                            "service_type": _service.split('@')[0],
                            "service": _service.split('@')[1].split(':')[0],
                            "port": port
                        })

        for k,v in __monitor.items():
            _monitors.append({
                "ip": k,
                "services": v['services']
            })

        # 开始并发处理
        processes = 10
        monitor_multi_process = my_concurrent.MyMultiProcess(processes)
        for i in _monitors:
            monitor_multi_process.multi_process_add(_service_monitor, i)
        monitor_multi_process.multi_process_wait()  # 等待执行完成
        result = monitor_multi_process.get_result()
        g_res = dict()
        for _res in result:
            __res = json.loads(_res.get())
            for k, v in __res.items():
                if not g_res.has_key(k): g_res[k] = []
                if not v == '': g_res[k].append(v)
        return HttpResponse(json.dumps({"result": "success", "info": g_res}))
    except Exception:
        _logger.error(traceback.format_exc())
        g_res = {"failed":["500 内部错误"], "success": []}
        return HttpResponse(json.dumps({"result": "failed", "info": g_res}))