# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json, os, time
import traceback
from djcelery.models import PeriodicTask, CrontabSchedule
#from django.db import transaction
from ops_job.models import OpsJobJobScriptInfo
from .script_edit import get_job_name, get_script_name

def datefield_to_str(date_data):
    '''
    mysql date格式转换为字符串格式
    :param date_data:
    :return:
    '''
    for i in date_data:
        if i.has_key("date_changed") and i.get('date_changed', None) is not None:
            i["date_changed"] = i["date_changed"].strftime("%Y-%m-%d %H:%M:%S")
        if i.has_key("last_run_at") and i.get('last_run_at', None) is not None:
            i["last_run_at"] = i["last_run_at"].strftime("%Y-%m-%d %H:%M:%S")
    return date_data

@csrf_exempt
def get_cron_list(request):
    cron_list = list(PeriodicTask.objects.all().values())
    cron_list = datefield_to_str(cron_list)
    crons = list(CrontabSchedule.objects.all().values())
    crons_dir = {}
    for item in crons:
        crons_dir[str(item['id'])] = "%s %s %s %s %s" % (item['minute'], item['hour'], item['day_of_month'], item['month_of_year'], item['day_of_week'])
    cron_list_ret = [{
        "periodic_task_ame": i['name'],
        "script_job_name": get_job_name(json.loads(i['kwargs']).get('script_name','无')),
        "crontab": crons_dir.get(str(i['crontab_id']), ""),
        "is_root": True if json.loads(i['kwargs']).get('is_root', '0') == '1' else False,
        "script_args": json.loads(i['kwargs']).get('script_args', '无'),
        "module_args": json.loads(i['kwargs']).get('module_args', '无'),
        "args_type": json.loads(i['kwargs']).get('args_type', '1'),
        "args_type_str": '直接传参' if json.loads(i['kwargs']).get('args_type', '1') == '1' else '文件传参',
        "enabled": i['enabled']
    } for i in cron_list if i['name'] != 'celery.backend_cleanup']
    return HttpResponse(json.dumps({
        "result": "success",
        "data": cron_list_ret
    }))



@csrf_exempt
def commitcron(request):
    try:
        periodic_task_name = request.POST.get('periodic_task_name')
        old_name = request.POST.get('old_name')
        enabled = True if request.POST.get('enabled') == 'true' else False
        _crontab = request.POST.get("crontab").strip()
        args_type = request.POST.get("args_type")
        try:
            crontab_time = {
                'day_of_week': _crontab.split()[4], # 周
                'month_of_year': _crontab.split()[3], # 月
                'day_of_month': _crontab.split()[2], # 日
                'hour': _crontab.split()[1], # 时
                'minute': _crontab.split()[0], # 分
            }
            # 检查crontab是否已经存在
            crons = CrontabSchedule.objects.filter(**crontab_time).first()
            if crons is None:
                CrontabSchedule.objects.create(**crontab_time)
        except Exception:
            return HttpResponse(json.dumps({"result": "failed", "info": "定时表达式错误"}))
        search_name = periodic_task_name if periodic_task_name == old_name else old_name
        if search_name is None:
            search_name = periodic_task_name
        # 查找任务
        task, created = PeriodicTask.objects.get_or_create(name=search_name)
        crontab = CrontabSchedule.objects.filter(**crontab_time).first()
        task.name = periodic_task_name  # name
        task.crontab = crontab  # 设置crontab
        task.enabled = enabled  # enabled
        task.task = "ops_job.tasks.tz_scrpits"  # tasks
        kwargs = {
                "script_name": get_script_name(request.POST.get('script_job_name', '')),
                "args_type": request.POST.get('args_type', '1'),
                "is_root": request.POST.get('is_root'),
                "script_args": '' if request.POST.get('script_args', '') in ['无', ''] else request.POST.get(
                    'script_args', ''),
                "module_args": '' if request.POST.get('module_args', '') in ['无', ''] else request.POST.get(
                    'module_args', ''),
            }
        task.kwargs = json.dumps(kwargs)
        task.save()
        return HttpResponse(json.dumps({"result": "success", "info": "已修改定时任务"}))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "内部错误"}))


def timeStampToTime(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(timestamp)))

@csrf_exempt
def get_task_list(request):
    '''
    获取脚本作业列表，用于创建定时任务
    :return:
    '''
    selected_script_job_name = request.POST.get("script_job_name", "")
    OpsJobJobScriptInfos = OpsJobJobScriptInfo.objects.filter(drop_status=0).values()
    tks = [i['job_name'] for i in OpsJobJobScriptInfos]
    return HttpResponse(json.dumps({"result": "success", "data": tks, "selected_script_job": selected_script_job_name}))


@csrf_exempt
def enablecron(request):
    try:
        job_name = request.POST.get('periodic_task_ame', None)
        enabled = request.POST.get('enabled', False)
        if not job_name:
            return HttpResponse(json.dumps({"result": "failed", "info": "未获取到job name"}))
        else:
            PeriodicTask.objects.filter(name=job_name).update(enabled=True if enabled == 'true' else False)
            if enabled == 'true':
                ret_info = "启用成功!"
            else:
                ret_info = "已停用!"
            return HttpResponse(json.dumps({"result": "success", "info": ret_info}))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "出错了，请到后台查看"}))


@csrf_exempt
def delete_cron_job(request):
    '''
    删除crontab任务
    :param request:
    :return:
    '''
    task_name = request.POST.get('periodic_task_ame')
    PeriodicTask.objects.filter(name=task_name).delete()
    return HttpResponse(json.dumps({"result": "success", "info": "出错了，请到后台查看"}))