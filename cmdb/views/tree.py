# coding=utf-8

# Create your views here.

import traceback
import logging
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from cmdb.views.product_info import get_product_name_byid, get_product_id
from cmdb.models import CmdbPool, CmdbTreeNode, CmdbProductInfo, CmdbAnsibleSshInfo
import json,time,datetime
from classes import crypto, get_ip_show_type
import getopt


_logger = logging.getLogger(__name__)

####################tree API############################

def get_ips_by_set_module(module_args, normal_params=None, file_params=None):
    '''
    根据set和module查询ip地址
    :return:
    '''
    opts, ags = getopt.getopt(module_args.split(), '-h-s:-m:-e')
    sets = None
    modules = None
    env = None
    for _opt_name, _opt_value in opts:
        if _opt_name in ('-h'):
            return {'result': 'success',
                'info': 'module_args:\n -s "set1,set2" \n-m "module1,module2" \n-e "环境类型：正式环境，测试环境"\n--root 强制以root身份执行\n--所有参数可使用,分隔多个参数'}
        if _opt_name in ('-s'):
            sets = _opt_value
        if _opt_name in ('-m'):
            modules = _opt_value
        if _opt_name in ('-e'):
            env = _opt_value

    if sets is None:
        if normal_params is None and file_params is None:
            return []
        else:
            return [], []
    sets = sets.split(',')
    modules_in_sets = CmdbTreeNode.objects.filter(depth=1, node_name__in=sets).values('id') if env is None else \
      CmdbTreeNode.objects.filter(depth=1, node_name__in=sets, environment=env.split(',')).values('id')
    sets_id = [ i['id'] for i in modules_in_sets ]
    modules_in_sets = CmdbTreeNode.objects.filter(depth=2, father_id__in=sets_id).values('id') if modules is None else \
      CmdbTreeNode.objects.filter(depth=2, father_id__in=sets_id, node_name__in=modules.split(',')).values('id')
    modules_id = [ i['id'] for i in modules_in_sets ]
    _ips = CmdbTreeNode.objects.filter(depth=3, father_id__in=modules_id).values()
    ret = list()
    ips = list()
    if normal_params is not None:
        ips = [i['node_name'] for i in _ips]
        ret = [{'ip':i['node_name'],'params': normal_params} for i in _ips]
    if file_params is not None:
        opts, ags = getopt.getopt(file_params.split(), '', ['service'])
        for item in _ips:
            data = ''
            for _opt_name, _opt_value in opts:
                if _opt_name in ('--service'):
                    print item['service_info']
                    data = "%s%s " % (data, item['service_info'])
            ret.append({
                'ip': item['node_name'],
                'params': data
            })
            ips.append(item['node_name'])
    if normal_params is None and file_params is None:
        return [i['node_name'] for i in _ips]
    return ips, ret


def get_tree_options(module_args):
    """
    获取tree信息
    :return:
    """
    opts, ags = getopt.getopt(module_args.split(), '-h-s:-m:-e')

########################################################

@login_required
def resource_total(request):
    cmdb_info = CmdbPool.objects.all().values()

    cmdb_info_table = [{u"id": int(i['id']), u"inner_addr_ip": i['inner_addr_ip'],
                         u"outer_addr_ip": i['outer_addr_ip'],
                         u"operating_system": i['operating_system'],
                         u"status": i['status'], u"region":i['region']} for i in cmdb_info ]
    return render_to_response("resource/total.html", {"page":"page1", "table_data": json.dumps(cmdb_info_table)})



#@login_required
@csrf_exempt
def tree_info(request):
    tree_root = datefield_to_str(list(CmdbTreeNode.objects.filter(father_id=0, depth=1).values()))
    treeDataRoot = [
        {'id': i['id'],
         'depth': i['depth'],
         'node_id': i['id'],
         'label': i['node_name'],
         'environment': i['environment'],
         'product_id':i['product_id'],
         'product_name':get_product_name_byid(i['product_id']),
         'update_time': i['update_time'],
         'node_type': i['node_type'],
         'father_id': i['father_id'],
         'children': []
         } for i in tree_root ]
    tree_root_ids = [i['id'] for i in tree_root]
    tree_second = datefield_to_str((list(CmdbTreeNode.objects.filter(father_id__in=tree_root_ids).values())))
    treeDataSecond = [
        {'id': i['id'],
         'depth': i['depth'],
         'node_id': i['id'],
         'label': i['node_name'],
         'environment': i['environment'],
         'product_id': i['product_id'],
         'product_name': get_product_name_byid(i['product_id']),
         'update_time': i['update_time'],
         'node_type': i['node_type'],
         'father_id': i['father_id'],
         'children': []
         } for i in tree_second]
    tree_second_ids = [i['id'] for i in tree_second]
    tree_third = datefield_to_str(list(CmdbTreeNode.objects.filter(father_id__in=tree_second_ids).values()))
    treeDataThird = [
        {'id': i['id'],
         'depth': i['depth'],
         'node_id': i['id'],
         'label': i['node_name'],
         'environment': i['environment'],
         'product_id': i['product_id'],
         'product_name': get_product_name_byid(i['product_id']),
         'update_time': i['update_time'],
         'node_type': i['node_type'],
         'father_id': i['father_id'],
         } for i in tree_third]

    for third in treeDataThird:
        for second in treeDataSecond:
            if third['father_id'] == second['node_id']:
                second['children'].append(third)   #填充2层
    for second in treeDataSecond:
        for root in treeDataRoot:    #填充根
            if second['father_id'] == root['node_id']:
                root['children'].append(second)
    # create tree node
    return HttpResponse(json.dumps({"result": "success", "data": treeDataRoot}))


@csrf_exempt
# 点击时拉取node信息
def get_node_info(request):
    node_id = request.POST.get("node_id")
    node_info = list(CmdbTreeNode.objects.filter(id=node_id).values())
    node_info = datefield_to_str(node_info)
    if len(node_info) == 0:
        node_info = {}
    else:
        node_info = node_info[0]
    #定义页面显示的内容
    lines = [
        "product_id",
        "product_name",
        "node_type",
        "environment",
        "service_info",
        "create_time",
    ]
    node_info['product_name'] = get_product_name_byid(node_info.get('product_id', 0))
    if node_info.get("depth", -1) == 3:
        from django.db.models import Q
        try:
            outter_ip = CmdbPool.objects.get(Q(inner_addr_ip=node_info['node_name'])|Q(outer_addr_ip=node_info['node_name']))
        except CmdbPool.DoesNotExist:
            outter_ip = None
        if outter_ip:
            node_info['inner_addr_ip'] = outter_ip.inner_addr_ip
            node_info['outer_addr_ip'] = outter_ip.outer_addr_ip
        else:
            node_info['inner_addr_ip'] = ''
            node_info['outer_addr_ip'] = ''
        try:
            ansible_ssh_info = CmdbAnsibleSshInfo.objects.get(
                Q(inner_addr_ip=node_info['node_name'])|Q(outer_addr_ip=node_info['node_name']))
        except CmdbAnsibleSshInfo.DoesNotExist:
            ansible_ssh_info = None
        node_info['ansible_ssh_user'] = ''
        node_info['ansible_ssh_port'] = ''
        node_info['ansible_sudo_pass'] = ''
        if ansible_ssh_info:
            node_info['ansible_ssh_user'] = ansible_ssh_info.ansible_ssh_user
            node_info['ansible_ssh_port'] = ansible_ssh_info.ansible_ssh_port
            node_info['ansible_sudo_pass'] = '' if ansible_ssh_info.ansible_sudo_pass == '' else crypto.passwd_aes(ansible_ssh_info.ansible_sudo_pass)
        lines.append('inner_addr_ip')
        lines.append('outer_addr_ip')
        lines.append('ansible_ssh_user')
        lines.append('ansible_ssh_port')
        lines.append('ansible_sudo_pass')
    if node_info['service_info']:
        node_info['service_info'] = node_info['service_info'].split(';')
    else:
        node_info['service_info'] = list()
    return HttpResponse(json.dumps({"result":"success", "data": {"node_info": node_info, "lines": lines}}))

@csrf_exempt
def change_father_node(request):
    try:
        node_id = request.POST.get('node_id', None)
        father_id = request.POST.get('father_id', None)

        father_node = CmdbTreeNode.objects.get(id=father_id)
        env = father_node.environment
        product_id = father_node.product_id
        CmdbTreeNode.objects.filter(id=node_id).update(father_id=father_id, environment=env, product_id=product_id)
        return HttpResponse(json.dumps({"result":"success", "info": "修改父节点成功"}))
    except Exception:
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "修改父节点失败"}))

@csrf_exempt
def get_unused_ip_from_cmdb_pool(request):
    '''
    获取资源池空闲机
    :return:
    '''
    inuse_info = CmdbTreeNode.objects.filter(node_type='ip').values()
    inuse_ip = [ i['node_name'] for i in inuse_info ]
    unuse_info = list(CmdbPool.objects.exclude(Q(inner_addr_ip__in=inuse_ip)|Q(outer_addr_ip__in=inuse_ip)).values())

    #print unuse_info   查询节点ip展示方式，外网ip或者内网ip
    show_type = get_ip_show_type.get_show_type()
    if show_type == 'outer_ip':
        unuse_ip = [ {"label": i['outer_addr_ip'], "value": i['outer_addr_ip']} for i in unuse_info ]
    else:
        unuse_ip = [{"label": i['inner_addr_ip'], "value": i['inner_addr_ip']} for i in unuse_info]

    return HttpResponse(json.dumps({"result": "success", "data": unuse_ip}))

@csrf_exempt
def get_prod_list(request):
    '''
    拉取所有product信息
    :return:
    '''
    cmdb_product_info = CmdbProductInfo.objects.all().values()
    print [ {'value':i['product_id'], 'lable': i['product_name']} for i in cmdb_product_info ]
    return HttpResponse(json.dumps({"result": "success", "data": [ {'value':i['product_id'], 'label': i['product_name']} for i in cmdb_product_info ]}))



@csrf_exempt
def save_node_change(request):
    '''
    修改节点信息
    :param request:
    :return:
    '''
    try:
        rowid = request.POST.get('rowid')
        rowKey = request.POST.get('rowKey')
        rowValue = request.POST.get('rowValue')
        if rowKey == "ansible_sudo_pass":
            if rowValue == '':
                rowValue = ''
            else:
                rowValue = crypto.passwd_aes(rowValue)
        updateinfo = {
            rowKey: rowValue
        }

        if rowKey.startswith("ansible"):
            node_info = CmdbTreeNode.objects.get(id=rowid)
            if node_info is None:
                return HttpResponse(json.dumps({"result": "failed", "info": "节点不存在"}))
            IpInfo = CmdbPool.objects.get(
                Q(inner_addr_ip=node_info.node_name) | Q(outer_addr_ip=node_info.node_name))
            if node_info is None:
                return HttpResponse(json.dumps({"result": "failed", "info": "ip不在资源池中"}))
            inner_addr_ip = IpInfo.inner_addr_ip
            outer_addr_ip = IpInfo.outer_addr_ip
            CmdbAnsibleSshInfoDb, created = CmdbAnsibleSshInfo.objects.get_or_create(inner_addr_ip=inner_addr_ip, outer_addr_ip=outer_addr_ip)
            CmdbAnsibleSshInfoDb.save()
            CmdbAnsibleSshInfo.objects.filter(inner_addr_ip=inner_addr_ip, outer_addr_ip=outer_addr_ip).update(**updateinfo)
        else:
            CmdbTreeNode.objects.filter(id=rowid).update(**updateinfo)
        return HttpResponse(json.dumps({"result": "success", "info": "保存成功"}))
    except Exception:
        _logger.error("Error while save change, %s" % traceback.format_exc())
        print traceback.format_exc()
        return HttpResponse(json.dumps({"result": "failed", "info": "保存失败"}))

@transaction.atomic  # 数据库事务
@csrf_exempt
def create_node(request):
    """
    创建节点
    :param request:
    :return:
    """
    update_time = timezone.make_aware(datetime.datetime.strptime("02/03/2014 12:00 UTC", "%d/%m/%Y %H:%M %Z"), timezone.get_default_timezone())
    time_now = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
    node_type = request.POST.get('node_type')
    if node_type == 'ip':
        ip = request.POST.get('node_name').strip()
        if not check_ip_exist(ip):
            return HttpResponse(json.dumps({"result": "failed","info":"创建的ip不存在资源库中，请先加入资源库"}))
    product_id = int(request.POST.get("product_id", "-1"))
    print product_id
    CmdbTreeNode.objects.create(product_id=product_id, node_name=request.POST.get("node_name", "-1"),
                            environment=request.POST.get("environment", "-1"),depth=request.POST.get("depth"),
                            father_id=request.POST.get('father_id'),node_type=request.POST.get("node_type"))
    created_id = CmdbTreeNode.objects.latest('id').id
    product_name = get_prod_name(request.POST.get("product_id", -1))
    return HttpResponse(json.dumps({"result": "success", "info":"添加成功", "data": {"created_id": created_id, "updatetime": time_now, "product_name": product_name}}))

@csrf_exempt
def delete_node(request):
    """
    删除节点
    :param request:
    :return:
    """
    node_id = int(request.POST.get("node_id", -1))
    tree_all = list(CmdbTreeNode.objects.all().values())
    nodeids = [node_id]
    traverse_node(node_id, tree_all, nodeids)  #获取所有需要删除的节点
    if not node_id == -1:
        CmdbTreeNode.objects.filter(id__in=nodeids).delete()
    return HttpResponse(json.dumps({"result": "success", "info": "删除成功"}))



###############old################

@csrf_exempt
def add_resource_from_page(request):
    kwargs = {
        'inner_addr_ip': request.POST.get('inner_addr_ip'),
        'outer_addr_ip': request.POST.get('outer_addr_ip'),
        'operating_system': request.POST.get('operating_system'),
        'status': request.POST.get('status'),
        'region': request.POST.get('region'),
        'create_time': str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))),
    }
    CmdbPool.objects.create(**kwargs)
    return HttpResponse(json.dumps({"result":"add success"}))



def datefield_to_str(date_data):
    for i in date_data:
        if i.has_key("create_time"):
            i["create_time"] = i["create_time"].strftime("%Y-%m-%d %H:%M:%S")
        if i.has_key("update_time"):
            i["update_time"] = i["update_time"].strftime("%Y-%m-%d %H:%M:%S")
    return date_data

def get_production():
    prod_info = list(CmdbProductInfo.objects.all().values())
    prod_info = datefield_to_str(prod_info)
    return prod_info

def get_prod_name(prod_id):
    prod_info = list(CmdbProductInfo.objects.filter(product_id=prod_id).values("product_name"))
    if len(prod_info) == 0:
        return "未指定业务"
    return prod_info[0]['product_name']

def get_prod_id_by_name(prod_name):
    prod_info = list(CmdbProductInfo.objects.filter(product_name=prod_name).values("product_id"))
    if len(prod_info) == 0:
        return -1
    return prod_info[0]['product_id']

#递归获取所有father
def get_all_father_node(node, tree_all):
    for i in tree_all:
        if node['father_id'] == i['id']:
            node['node_name'] = "%s:%s" % (i['node_name'], node['node_name'])
        else:
            continue
        if i['father_id'] == 0:
            pass
        else:
            get_all_father_node(node, tree_all)

def get_folder_node():
    tree_root = list(CmdbTreeNode.objects.filter(node_type='folder').values())
    tree_all = list(CmdbTreeNode.objects.all().values())
    for i in tree_root:
        get_all_father_node(i, tree_all)
    tree_root = datefield_to_str(tree_root)
    return tree_root

def get_all_father_name(node_name):
    '''
    根据node name 找到所有父节点，并输出路径
    :return:
    '''
    node = list(CmdbTreeNode.objects.filter(node_name=node_name).values())
    #tree_all = list(CmdbTreeNode.objects.all().values())
    if not len(node) == 0:
        node = node[0]
    else:
        return ''
    #all_father_node = get_all_father_node(node, tree_all)
    return node['node_name']

def get_id_by_name(name):
    '''
    根据节点名称获取id
    :param name:
    :return:
    '''
    try:
        if name == 'all_set':
            ids = [i['id'] for i in list(CmdbTreeNode.objects.filter(~Q(node_type='ip')).values())]
        else:
            ids = [i['id'] for i in list(CmdbTreeNode.objects.filter(~Q(node_type='ip'), node_name=name).values())]
    except(Exception):
        return None
    else:
        return ids

def get_ip_by_name(name):
    '''
    根据节点找到ip
    :return:
    '''
    node = list(CmdbTreeNode.objects.filter(node_name=name).values())
    if len(node) == 0:
        return None
    else:
        if node[0]['node_type'] == 'ip':
            return [node[0]['node_name']]
        else:
            id = node[0]['id']
            ips = get_app_ip_by_father(id)
            return ips

def get_app_ip_by_father(father_ids):
    '''
    根据父节点找所有ip
    :param father_id:
    :return:
    '''
    tree_all = list(CmdbTreeNode.objects.all().values())
    all_ip = list()
    for father_id in father_ids:
        nodeids = list()
        traverse_node(father_id, tree_all, nodeids)
        all_ip += [i['node_name'] for i in list(CmdbTreeNode.objects.filter(id__in=nodeids, node_type='ip').values())]
    return list(set(all_ip))

@csrf_exempt   # 创建根节点前获取信息
def get_info_before_create_root_node(request):
    apps = get_production()
    tree_father = get_folder_node()
    return HttpResponse(json.dumps({"apps":apps, "tree_father":tree_father}))

@csrf_exempt   # 创建子节点前获取信息
def get_info_before_create_child_node(request):
    father_id = request.POST.get('father_id', -1)
    father_info = list(CmdbTreeNode.objects.filter(id=father_id).values())[0]
    return HttpResponse(json.dumps({"environment": father_info['environment'], "depth": father_info['depth']+1, "father_id": father_id,
                                    "father_node_type": father_info['node_type'], "product_id": father_info['product_id'], "father_name": father_info['node_name'],
                                    "product_name": get_prod_name(father_info['product_id']), "node_depth": father_info['depth']
                                    }))


def check_ip_exist(ip):
    '''
    查询ip是否存在资源库
    :return:
    '''
    exist = list(CmdbPool.objects.filter(Q(inner_addr_ip=ip)|Q(outer_addr_ip=ip)).values())
    if not len(exist) == 0:
        return True
    else:
        return False





# 递归查找所有子节点
def traverse_node(father_id, tree_all, nodeids):
    for i in tree_all:
        if father_id == i['father_id']:
            nodeids.append(i['id'])
            traverse_node(i['id'], tree_all, nodeids)
        else:
            pass


def change_node_info(request):
    '''
    修改节点信息
    :param request:
    :return:
    '''
    change_key = request.POST.get("change_key", None)
    change_value = request.POST.get("change_value", None)
    node_id = request.POST.get("node_id", None)

    # 修改ansible ssh信息
    if change_key in ['ansible_ssh_user','ansible_ssh_port','ansible_sudo_pass']:
        try:
            ip = list(CmdbTreeNode.objects.filter(id=node_id).values('node_name'))
            if len(ip) == 0:
                return json.dumps({"result": "failed", "info": "no such ip"})
            ip = ip[0]['node_name']
            ip_detail = list(CmdbPool.objects.filter(
                Q(inner_addr_ip=ip)|Q(outer_addr_ip=ip))\
                .values('inner_addr_ip', 'outer_addr_ip'))
            if len(ip_detail) == 0:
                return json.dumps({"result": "failed", "info": "no such ip in cmdb"})
            inner_addr_ip = ip_detail[0]['inner_addr_ip']
            outer_addr_ip = ip_detail[0]['outer_addr_ip']

            ssh_info = list(CmdbAnsibleSshInfo.objects.filter(inner_addr_ip=inner_addr_ip,outer_addr_ip=outer_addr_ip).values())
            update_info = {
                "inner_addr_ip": inner_addr_ip,
                "outer_addr_ip": outer_addr_ip,
                change_key: change_value
            }
            if len(ssh_info) == 0:
                CmdbAnsibleSshInfo.objects.create(**update_info)
            else:
                CmdbAnsibleSshInfo.objects.filter(inner_addr_ip=inner_addr_ip, outer_addr_ip=outer_addr_ip).update(**update_info)
            return HttpResponse(json.dumps({"result": "success", "info": "change success"}))
        except(Exception):
            _logger.error("change ansible ssh info failed: %s" % traceback.format_exc())
            return HttpResponse(json.dumps({"result": "failed", "info": "Change ansible ssh info failed"}))


    # tree node 修改
    if change_key is None or change_value is None or node_id is None:
        return HttpResponse(json.dumps({"result": "failed", "info": "No key or value"}))
    kwargs = {
        change_key: change_value.replace("\n",";")
    }
    CmdbTreeNode.objects.filter(id=node_id).update(**kwargs)


    return HttpResponse(json.dumps({"result": "success", "info": "change success"}))