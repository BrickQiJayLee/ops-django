# coding=utf-8

# Create your views here.

import traceback
import logging, json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from cmdb.models import CmdbProductInfo

_logger = logging.getLogger(__name__)

@csrf_exempt
def commit_product(request):
    try:
        product_id = request.POST.get("product_id")
        product_name = request.POST.get("product_name")
        cmdb_productinfo, created = CmdbProductInfo.objects.get_or_create(product_id=product_id, product_name=product_name)
        cmdb_productinfo.develop = request.POST.get("develop")
        cmdb_productinfo.ops = request.POST.get("ops")
        cmdb_productinfo.test = request.POST.get("test")
        cmdb_productinfo.save()
        return HttpResponse(json.dumps({"result": "success", "info": "提交成功"}))
    except Exception:
        print traceback.format_exc()
        _logger.error(traceback.format_exc())
        return HttpResponse(json.dumps({"result": "failed", "info": "提交失败"}))

@csrf_exempt
def delete_product(request):
    try:
        product_id = request.POST.get("product_id")
        product_name = request.POST.get("product_name")
        print CmdbProductInfo.objects.filter(product_id=product_id, product_name=product_name).values()
        CmdbProductInfo.objects.filter(product_id=product_id, product_name=product_name).delete()
        return HttpResponse(json.dumps({"result": "success", "info": "删除成功"}))
    except Exception:
        print traceback.format_exc()
        _logger.error(traceback.format_exc())
        return HttpResponse(json.dumps({"result": "failed", "info": "删除失败"}))

@csrf_exempt
def product_list(request):
    try:
        return HttpResponse(json.dumps({"result": "success", "data": list(CmdbProductInfo.objects.all().values())}))
    except Exception:
        print traceback.format_exc()
        _logger.error(traceback.format_exc())
        return HttpResponse(json.dumps({"result": "failed", "info": "查询列表失败"}))

def get_product_name_byid(ProductId):
    cmdb_product_info = CmdbProductInfo.objects.filter(product_id=ProductId).first()
    if cmdb_product_info:
        return cmdb_product_info.product_name
    else:
        return '未指定业务'

def get_product_id(product_name):
    cmdb_product_info = CmdbProductInfo.objects.filter(product_name=product_name).first()
    if cmdb_product_info:
        return cmdb_product_info.product_id
    else:
        return -1