# coding=utf-8

# Create your views here.

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from classes import crypto
from cmdb.views.tree import get_prod_id_by_name
from cmdb.models import CmdbProductInfo
from db_job.models import DbJobDbInstance
import json, time, logging, traceback


_logger = logging.getLogger(__name__)



################数据库实例注册################
@csrf_exempt
def add_db_instance(request):
    '''
    新增实例
    :param request:
    :return:
    '''
    try:
        db_mark = request.POST.get('db_mark', None)
        db_job_instance,created = DbJobDbInstance.objects.get_or_create(db_mark=db_mark)
        if not created:
            return HttpResponse(json.dumps({"result":"failed", "info": "实例名重复"}))
        db_job_instance.db_master = request.POST.get('db_master', None)
        db_job_instance.db_slave = request.POST.get('db_slave', None)
        db_job_instance.db_product = request.POST.get('db_product', None).split('_')[0]
        try:
            db_job_instance.db_product_id = list(CmdbProductInfo.objects.filter(product_name=request.POST.get('db_product', None).split('_')[0]).values("product_id"))[0]['product_id']
        except Exception:
            db_job_instance.db_product_id = -1
        db_job_instance.db_env = request.POST.get('db_env', None)
        db_job_instance.db_mark = request.POST.get('db_mark', None)
        db_job_instance.db_user_name = request.POST.get('db_user_name', None)
        db_job_instance.db_container_name = request.POST.get('db_container_name', None)
        db_job_instance.db_service_type = request.POST.get('db_service_type', None)
        db_job_instance.db_service_name = request.POST.get('db_service_name', None)
        db_job_instance.db_passwd = crypto.passwd_aes(request.POST.get('db_passwd', None))  # 加密密码
        db_job_instance.save()
        return HttpResponse(json.dumps({"result":"success"}))
    except Exception:
        print traceback.format_exc()
        _logger.error(traceback.format_exc())
        return HttpResponse(json.dumps({"result":"failed", "info":"数据库操作异常"}))

@csrf_exempt
def delete_instance(request):
    '''
    删除db resource
    :param request:
    :return:
    '''
    try:
        id = request.POST.get('id')
        DbJobDbInstance.objects.filter(id=id).delete()
        return HttpResponse(json.dumps({"result": "success", "info": "已成功删除"}))
    except Exception:
        print traceback.format_exc()
        _logger.error(traceback.format_exc())
        return HttpResponse(json.dumps({"result":"failed", "info": "删除失败"}))



def resource():
    data = DbJobDbInstance.objects.all().values()
    data = [{u"id": int(i['id']), u"db_master": i['db_master'],
      u"db_slave": i['db_slave'],
      u"db_product": i['db_product'],
      u"db_product_id": i['db_product_id'], u"db_env": i['db_env'], u"db_mark": i['db_mark'], u"db_passwd": i['db_passwd'],
             u"db_container_name": i['db_container_name'],u"db_container_name_slave": i['db_container_name_slave'], u"db_user_name": i['db_user_name'], u"db_service_type": i['db_service_type'],
             u"db_service_name": i['db_service_name'], u"db_service_name_slave": i['db_service_name_slave']} for i in data]
    return data


@csrf_exempt
def commit_db_instance(request):
    '''
    修改或新增db实例
    :param request:
    :return:
    '''
    db_id = request.POST.get("id", -1)
    pass_change = request.POST.get("pass_change", 0)
    #print pass_change
    db_info = {
        "db_master": request.POST.get("db_master"),
        "db_slave": request.POST.get('db_slave', None),
        "db_product": request.POST.get("db_product"),
        "db_product_id": get_prod_id_by_name(request.POST.get("db_product")),
        "db_env": request.POST.get("db_env"),
        "db_mark": request.POST.get("db_mark"),
        "db_container_name": request.POST.get("db_container_name"),
        "db_container_name_slave": request.POST.get("db_container_name_slave"),
        "db_user_name": request.POST.get("db_user_name"),
        "db_service_type": request.POST.get("db_service_type"),
        "db_service_name": request.POST.get("db_service_name"),
        "db_service_name_slave": request.POST.get("db_service_name_slave")
    }
    if int(pass_change) == 1:
        db_info["db_passwd"] = crypto.passwd_aes(request.POST.get("db_passwd"))
    db_instance = DbJobDbInstance.objects.filter(db_mark=db_info['db_mark']).values()
    if db_instance:
        return HttpResponse(json.dumps({"result": "failed", "info": "实例名重复"}))
    if db_id in [None, '', '-1', '0', -1, 0]:
        try:
            DbJobDbInstance.objects.create(**db_info)
        except Exception:
            _logger.error(traceback.format_exc())
            return HttpResponse(json.dumps({"result": "failed", "info": "获取db实例失败"}))
    else:
        DbJobDbInstance.objects.filter(id=db_id).update(**db_info)
    return HttpResponse(json.dumps({"result": "success", "info": "提交成功"}))



@csrf_exempt
def db_registry(request):
    '''
    注册数据库主页面
    :param request:
    :return:
    '''
    data = resource()
    elseData = {
        "app_info": [ {'value': i['product_name'], 'lable':i['product_name']} for i in CmdbProductInfo.objects.all().values() ],
        "env_info": [
            {
                'value': 'test',
                'lable': 'test'
            },
            {
                'value': 'prod',
                'lable': 'prod'
            }
        ],
        "service_type": [
            {
                'value': 'container',
                'lable': 'container'
            },
            {
                'value': 'service',
                'lable': 'service'
            }
        ],
    }
    return HttpResponse(json.dumps({"result": "success", "data":  data, "elseData": elseData}))
