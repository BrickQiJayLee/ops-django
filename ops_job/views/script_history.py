# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json, os, time, logging
import traceback
from djcelery.models import PeriodicTask, CrontabSchedule
#from django.db import transaction
from ops_job.models import OpsJobScriptHistory
from operator import itemgetter


_logger = logging.getLogger(__name__)


@csrf_exempt
def get_script_history(request):
    startTime = request.POST.get('startTime', None)
    endTime = request.POST.get('endTime', None)
    print startTime, endTime
    if not endTime or not startTime:
        return HttpResponse(json.dumps({"result": "failed", "info": "请指定时间"}))
    script_history = OpsJobScriptHistory.objects.filter(dtEventTime__gte=startTime,dtEventTime__lte=endTime).values()
    if not script_history:
        return HttpResponse(json.dumps({"result": "success", "data": []}))
    data = list()
    for item in script_history:
        job_name = item['job_name']
        ip_list = item['ip_list']
        ip_list = '[]' if ip_list == '' else ip_list
        if ip_list == '':
            ip_list = []
        exec_status = item['exec_status']
        try:
            _result = json.loads(item['result'])
        except:
            _logger.error("result not a json")
            continue
        host_ok_list = _result.get('host_ok', {})
        host_ok_ip_count = len(host_ok_list)
        host_failed_list = _result.get('host_failed', {})
        host_failed_ip_count = len(host_failed_list)
        host_unreachable_list = _result.get('host_unreachable', {})
        host_unreachable_ip_count = len(host_unreachable_list)
        for i in [host_ok_list, host_failed_list, host_unreachable_list]:
            for k,v in dict(i).items():
                if v.has_key('stdout'): del v['stdout']
                if v.has_key('stderr'): v['stderr'] = v['stderr'].split('\n')
        detail = {
            "成功IP:": host_ok_list,
            "失败IP:": host_failed_list,
            "不可达IP:": host_unreachable_list,
            "未执行IP": list(set(ip_list) ^ set(host_ok_list.keys() + host_failed_list.keys() + host_unreachable_list.keys())),
            "IP列表:": ip_list
        }
        dteventtime = item['dtEventTime']
        data.append({
            "id": item['id'],
            "job_name": job_name,
            "host_ok_ip_count": host_ok_ip_count,
            "host_failed_ip_count": host_failed_ip_count,
            "host_unreachable_ip_count": host_unreachable_ip_count,
            "detail": detail,
            "exec_status": False if exec_status == 0 else True,
            "dteventtime": dteventtime.strftime("%Y-%m-%d %H:%M:%S")
        })
    data = sorted(data, key=lambda i: i['dteventtime']) #排序
    data.reverse()
    return HttpResponse(json.dumps({"result": "success", "data": data}))

@csrf_exempt
def script_history_detail(request):
    try:
        history_id = request.GET.get("history_id", None)
        if not history_id:
            return HttpResponse(json.dumps({"result": "failed", "data": {"ExecComplete":True, "info": "传入记录ID错误"}}))

        script_history = OpsJobScriptHistory.objects.filter(id=history_id).first()
        if not script_history:
            return HttpResponse(json.dumps({"result": "failed", "data": "未查到执行历史记录"}))
        job_name = script_history.job_name
        dteventtime = script_history.dtEventTime
        ip_list = script_history.ip_list
        ip_list = '[]' if ip_list == '' else ip_list
        exec_status = script_history.exec_status
        _result = json.loads(script_history.result)
        host_ok_list = _result.get('host_ok', {})
        host_ok_ip_count = len(host_ok_list)
        host_failed_list = _result.get('host_failed', {})
        host_failed_ip_count = len(host_failed_list)
        host_unreachable_list = _result.get('host_unreachable', {})
        host_unreachable_ip_count = len(host_unreachable_list)

        for i in [host_ok_list, host_failed_list, host_unreachable_list]:
            for k, v in dict(i).items():
                if v.has_key('stdout'): del v['stdout']
                if v.has_key('stderr'): v['stderr'] = v['stderr'].split('\n')
        detail = {
            "成功IP[%s]:" % host_ok_ip_count: host_ok_list,
            "失败IP[%s]:" % host_failed_ip_count: host_failed_list,
            "不可达IP[%s]:" % host_unreachable_ip_count: host_unreachable_list,
            "未执行IP": list(set(json.loads(ip_list)) ^ set(host_ok_list.keys() + host_failed_list.keys() + host_unreachable_list.keys())),
            "IP列表:": ip_list,
            "ExecComplete": True if exec_status == 0 else False
        }
        return HttpResponse(json.dumps({
            "result": "success",
            "data": detail
        }))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({
            "result": "failed",
            "data": {"ExecComplete":True, "info": "查询失败，已停止"}
        }))