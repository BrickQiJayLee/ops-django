# coding=utf-8
from __future__ import absolute_import
from django.http import HttpResponse
#import traceback
import json
import traceback
from django.views.decorators.csrf import csrf_exempt
from classes import ansible_api
from cmdb.views.tree import get_ips_by_set_module
from ops_job.models import OpsJobScriptHistory
from .script_edit import get_job_name, get_script_name
import logging

_logger = logging.getLogger(__name__)


def get_history_id(script_job_name):
    '''
    创建任务并获得history_id'''
    _history = OpsJobScriptHistory()
    _history.job_name = script_job_name
    _history.result = json.dumps({})
    _history.exec_status = 1
    _history.save()
    _history_id = _history.id
    return _history_id

@csrf_exempt
def exector_create(request):
    '''
    创建任务记录
    :return:
    '''
    script_job_name = request.POST.get("script_job_name")
    _history_id = get_history_id(script_job_name)
    return HttpResponse(json.dumps({"result": "success", "data": {"history_id": _history_id}}))

def exec_scripts(kwargs):
    '''
    执行脚本统一入口
    :return:
    '''
    try:
        args_type = kwargs.get("args_type", None)
        script_name = kwargs.get("script_name", None)
        history_id = kwargs.get("history_id", None)
        if history_id is None:
            return {'result': 'failed', 'info': u'请先创建任务'}
        if script_name is None:
            job_name = kwargs.get("script_job_name", None)
            script_name = get_script_name(job_name)
        else:
            job_name = get_job_name(script_name)
        if script_name is None and job_name is None:
            _logger.error('%s script %s"' % (script_name, u"传入名称参数错误"))
        script_args = kwargs.get("script_args", '')
        module_args = kwargs.get("module_args", None)   #模块参数 例: "-s vms_test -m env1" 根据参数获取对应ip地址
        specific_ip = kwargs.get("specific_ip", [])   #指定ip地址
        is_root = kwargs.get("is_root", 0)   #指定ip地址
        if script_name is None:
            _logger.error('%s script %s"' % (script_name, u"未指定作业"))
            return {'result': 'failed', 'info':u'未指定作业'}
        if module_args is not None and module_args != '':
            ips = get_ips_by_set_module(module_args)
            ips = ips + specific_ip
        else:
            return {'result': 'failed', 'info':u'未指定ip'}
        if args_type == 'normal':
            script_args_req = script_args
        elif args_type == 'file':
            _, script_args_req = get_ips_by_set_module(module_args, file_params=script_args)
            script_args_req = ["%s %s" % (i['ip'], i['params']) for i in script_args_req]
            script_args_req = '\n'.join(script_args_req)
        else:
            return {'result': 'failed', 'info': u'参数错误'}
        if is_root == '1':
            ansible_interface = ansible_api.AnsiInterface(become=True, become_method='sudo', become_user='root', history_id=history_id)
            result = ansible_interface.exec_script_all_type(ips, script_name, script_args=script_args_req, args_type=args_type)
        else:
            ansible_interface = ansible_api.AnsiInterface(history_id=history_id)
            result = ansible_interface.exec_script_all_type(ips, script_name, script_args=script_args_req, args_type=args_type)
        #result = ansible_interface._get_result()
        _history = OpsJobScriptHistory.objects.get(id=history_id)
        _history.result = json.dumps(result)
        _history.ip_list = json.dumps(ips)
        _history.exec_status = 0
        _history.save()
        g_res = result
        return {"result": "success", "data": g_res}
    except Exception:
        _logger.error(traceback.format_exc())

@csrf_exempt
def get_args(request):
    """
    点击获取脚本参数
    :param request:
    :return:
    """
    try:
        args_type = request.POST.get("args_type")
        module_args = request.POST.get("module_args")
        script_args = request.POST.get("script_args")
        if args_type == 'normal':
            ips, args = get_ips_by_set_module(module_args, normal_params=script_args)
        elif args_type == 'file':
            ips, args = get_ips_by_set_module(module_args, file_params=script_args)
        else:
            return HttpResponse(json.dumps({"result": "failed", "info": "未获取到ip列表"}))
        return HttpResponse(json.dumps({"result": "success", "data": args}))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "获取参数有误"}))

@csrf_exempt
def scrpits_http(request):
    try:
        kwargs = json.loads(request.POST.get("kwargs", None))
        ret = exec_scripts(kwargs)
        return HttpResponse(json.dumps(ret))
    except Exception:
        _logger.error(traceback.format_exc())