# coding=utf-8

# Create your views here.

import traceback
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.decorators import login_required
# from django.db import transaction
from django.db.models import Q
from cmdb.models import CmdbPool, CmdbTreeNode
import json
# from account.views.login import check_login
# from django.contrib.auth.decorators import login_required

_logger = logging.getLogger(__name__)


@csrf_exempt
def cmdb_pool(request):
    cmdb_info = list(CmdbPool.objects.all().values())
    cmdb_info_table = [{u"id": int(i['id']), u"inner_addr_ip": i['inner_addr_ip'],
                         u"outer_addr_ip": i['outer_addr_ip'],
                         u"operating_system": i['operating_system'],
                         u"status": i['status'], u"region":i['region'],u"available_zone":i['available_zone']} for i in cmdb_info ]
    return HttpResponse(json.dumps({"result":"success", "data": cmdb_info_table}))

@csrf_exempt
def cmdb_update(request):
    data_id = request.POST.get('id')
    data_val = {
        "available_zone": request.POST.get('available_zone'),
        "inner_addr_ip": request.POST.get('inner_addr_ip'),
        "outer_addr_ip": request.POST.get('outer_addr_ip'),
        "operating_system": request.POST.get('operating_system'),
        "region": request.POST.get('region')
    }
    # check if exists
    if data_id in [None, '']:
        if CmdbPool.objects.filter(Q(inner_addr_ip=data_val['inner_addr_ip']) | Q(outer_addr_ip=data_val['outer_addr_ip'])):
            return HttpResponse(json.dumps({"result": "failed", "info": "资源已经存在"}))
        CmdbPool.objects.create(**data_val)
    else:
        if CmdbPool.objects.filter(~Q(id=data_id), Q(inner_addr_ip=data_val['inner_addr_ip']) | Q(outer_addr_ip=data_val['outer_addr_ip'])):
            return HttpResponse(json.dumps({"result": "failed", "info": "资源已经存在"}))
        CmdbPool.objects.filter(id=data_id).update(**data_val)
    return HttpResponse(json.dumps({"result": "success", "info": "提交成功"}))

@csrf_exempt
def cmdb_delete(request):
    try:
        data_id = request.POST.get('id')
        inner_ip = request.POST.get('inner_ip')
        outer_ip = request.POST.get('outer_ip')
        try:
            if CmdbTreeNode.objects.get(Q(node_name=inner_ip)|Q(node_name=outer_ip)):
                return HttpResponse(json.dumps({"result": "failed", "info": "在业务模型中还未移除该资源"}))
        except Exception:
            pass
        CmdbPool.objects.filter(id=data_id).delete()
        return HttpResponse(json.dumps({"result": "success", "info": "删除成功"}))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "删除失败"}))