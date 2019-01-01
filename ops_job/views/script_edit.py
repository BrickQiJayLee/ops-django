# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os, time, logging
import json, commands
import traceback
import time
from ops_job.models import OpsJobJobScriptInfo

_logger = logging.getLogger(__name__)

def cmd(cmdStr):
    status, out = commands.getstatusoutput(cmdStr)
    if status != 0 :
        print "[%s] ERROR:%s"%(cmdStr, out)
        return 1
    else:
        return out

def datefield_to_str(date_data):
    '''
    mysql date格式转换为字符串格式
    :param date_data:
    :return:
    '''
    for i in date_data:
        if i.has_key("mTime") and i.get('mTime', None) is not None:
            i["mTime"] = i["mTime"].strftime("%Y-%m-%d %H:%M:%S")
    return date_data

# Create your views here.
def timeStampToTime(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(timestamp)))

def get_job_name(script_name):
    OpsJobJobScriptInfos = OpsJobJobScriptInfo.objects.filter(script_name=script_name,drop_status=0).first()
    if OpsJobJobScriptInfos is None:
        return '未命名'
    else:
        return OpsJobJobScriptInfos.job_name

def get_script_name(job_name):
    OpsJobJobScriptInfos = OpsJobJobScriptInfo.objects.filter(job_name=job_name,drop_status=0).first()
    if OpsJobJobScriptInfos is None:
        return '未找到脚本名'
    else:
        return OpsJobJobScriptInfos.script_name

@csrf_exempt
def get_scripts_list(request):
    OpsJobJobScriptInfos = list(OpsJobJobScriptInfo.objects.filter(drop_status=0).values())
    OpsJobJobScriptInfos = datefield_to_str(OpsJobJobScriptInfos)
    file_list = list()
    for item in OpsJobJobScriptInfos:
        file_list.append({'script_job_name': item['job_name'], 'script_name': item['script_name'], 'mtime': item['mTime']})
    return HttpResponse(json.dumps({'data': file_list}))

@csrf_exempt
def edit_script(request):
    script_name = request.POST.get('script_name', None)
    script_type = script_name.split('.')[-1]
    script_type_list = {'py': 'python',
                        'sh': 'shell',
                        'pl': 'perl'}
    script_type = script_type_list.get(script_type, 'shell')
    script_info = OpsJobJobScriptInfo.objects.filter(script_name=script_name,drop_status=0).first()
    script_content = '' if script_info is None else script_info.script_content
    script_name = '' if script_info is None else script_info.script_name
    script_job_name = '' if script_info is None else script_info.job_name
    return HttpResponse(json.dumps({ 'data': {
        "script_content": script_content,
        "script_type": script_type,
        "script_name": script_name,
        "script_job_name": script_job_name
    }}))


@csrf_exempt
def updatescript(request):
    script_name = request.POST.get("script_name", None)
    script_content = request.POST.get("script_content", None)
    job_name = request.POST.get("script_job_name", None)
    # old_job_name = request.POST.get("old_job_name", None)
    old_script_name = request.POST.get("old_script_name", None)
    search_name = old_script_name if not script_name == old_script_name else script_name
    #curPath = os.path.abspath(os.path.dirname(__file__))
    #if not script_name == old_script_name and old_script_name != '':
    #    script_path = "%s/script/%s" % (curPath, old_script_name)
    #    os.remove(script_path) #删除旧文件
    #new_script_path = "%s/script/%s" % (curPath, script_name)
    #with open(new_script_path, 'w') as f: #创建新文件或修改原文件
    #    f.write(script_content.encode('utf-8'))
    #cmd("cd %s/script && git add . && git commit -m 'remove script: %s, update script: %s' && git push" %
    #    (curPath, old_script_name, script_name))
    #更新script.list
    job_script_info,created = OpsJobJobScriptInfo.objects.get_or_create(script_name=search_name,drop_status=0)
    job_script_info.script_name = script_name
    job_script_info.job_name = job_name
    job_script_info.mTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time.time())))
    job_script_info.script_content = script_content.encode('utf-8')
    job_script_info.save()
    #job_script_info.script_name = script_name
    return HttpResponse(json.dumps({"result": "success", "info":"commit success"}))

@csrf_exempt
def delete_script(request):
    try:
        script_name = request.POST.get("script_name", None)
        OpsJobJobScriptInfo.objects.filter(script_name=script_name).update(drop_status=1)
        return HttpResponse(json.dumps({"result": "success", "info": "脚本已删除"}))
    except Exception:
        return HttpResponse(json.dumps({"result": "failed", "info": "脚本删除失败: %s" % traceback.format_exc()}))
