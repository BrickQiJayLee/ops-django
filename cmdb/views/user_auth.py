# coding=utf-8

# Create your views here.
from __future__ import absolute_import
from django.http import HttpResponse
from django.utils import timezone
import datetime
from django.views.decorators.csrf import csrf_exempt
import traceback
import json
import os
from django.db.models import Q
import logging
from classes import ansible_api, my_concurrent
from cmdb.models import CmdbTreeNode, CmdbUserSshAuth

_logger = logging.getLogger(__name__)


# 获取本机公钥
USERHOME = os.environ['HOME']
with open("%s/.ssh/id_rsa.pub" % USERHOME) as f:
    LOCALSSHKEY = f.read().strip()

#############common############

def datefield_to_str(date_data):
    '''
    mysql date格式转换为字符串格式
    :param date_data:
    :return:
    '''
    for i in date_data:
        if i.has_key("create_time") and i.get('create_time', None) is not None:
            i["create_time"] = i["create_time"].strftime("%Y-%m-%d %H:%M:%S")
        if i.has_key("update_time") and i.get('update_time', None) is not None:
            i["update_time"] = i["update_time"].strftime("%Y-%m-%d %H:%M:%S")
    return date_data

def get_id_by_name(name):
    '''
    根据节点名称获取id
    :param name:
    :return:
    '''
    try:
        ids = [i['id'] for i in list(CmdbTreeNode.objects.filter(~Q(node_type='ip'), node_name=name).values())]
        return ids
    except(Exception):
        return None


# 递归查找所有子节点
def traverse_node(father_id, tree_all, nodeids):
    for i in tree_all:
        if father_id == i['father_id']:
            nodeids.append(i['id'])
            traverse_node(i['id'], tree_all, nodeids)
        else:
            pass

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

def get_all_node():
    nodes = datefield_to_str(list(CmdbTreeNode.objects.filter(node_type='app').values()))
    return nodes

def get_keys_sync_info():
    '''
    获取每个ip对应的用户key
    :return ip:user_key, 关联用户id
    '''
    user_key_info = list(CmdbUserSshAuth.objects.all().values())
    '''获取所有关联的模块'''
    all_apps = [i['related_node'] for i in user_key_info]
    while '' in all_apps:
        all_apps.remove('')
    all_apps = list(set((','.join(all_apps)).split(',')))
    keys_sync_info = dict()
    for i in all_apps:
        if not keys_sync_info.has_key(i):
            keys_sync_info[i] = {'ip':[]}  #保存IP
        father_ids = get_id_by_name(i)
        print father_ids
        set_ips = get_app_ip_by_father(father_ids)
        print set_ips
        for n in set_ips:
            if not n in keys_sync_info[i]['ip']:
                keys_sync_info[i]['ip'].append(n)
    ip_keys = dict() #保存ip对应key信息
    for i in user_key_info:
        user_id = i['id']
        user_key = i['user_key']
        related_nodes = i['related_node'].split(',')
        for node in related_nodes:
            if keys_sync_info.has_key(node):
                for ip in keys_sync_info[node]['ip']:
                    if not ip_keys.has_key(ip):
                        ip_keys[ip] = list()
                    ip_keys[ip].append(user_key)

    #special ip
    for item in user_key_info:
        special_ip = item.get('special_ip')
        key = item.get('user_key')
        if special_ip == '':
            continue
        elif special_ip is None:
            continue
        else:
            special_ips = special_ip.split(',')
        for ip in special_ips:
            if ip_keys.has_key(ip.strip()):
                ip_keys[ip.strip()].append(key)
            else:
                ip_keys[ip.strip()] = [key]

    #去重
    for k, v in ip_keys.items():
        ip_keys[k] = list(set(ip_keys[k]))
    ret_ip_keys = list()
    for ip, keys in ip_keys.items():
        keys_str = get_base_auth_key() if len(keys) == 0 else u"%s\n%s" % ('\n'.join(keys), get_base_auth_key())
        if len(keys_str.split('\n')) <= 3:
            print("length of keys less than 3, plase check")
            _logger.error("length of keys less than 3, plase check")
            return None, None
        ret_ip_keys.append([ip, keys_str])
    return ret_ip_keys

def change_user_stat(status='synced'):
    '''
    改变用户状态
    :return:
    '''
    CmdbUserSshAuth.objects.all().update(status=status)




def get_base_auth_key():
    '''
    获取没台管理的主机都需要添加的sshkey
    :return:
    '''
    with open("conf/sshkey_global.conf", 'r') as f:
        FileKey = f.read()
    return "%s\n%s" % (FileKey, LOCALSSHKEY)

def sync_auth_keys(keys_synv_info):
    '''
    实际执行同步user key的方法
    :return:
    '''
    try:
        ip = keys_synv_info[0]
        keys = keys_synv_info[1]
        ansible_interface = ansible_api.AnsiInterface(become=True, become_method='sudo', become_user='root')
        ansible_interface.sync_authorized_key(ip, 'user=root key="%s" exclusive=True state=present' % keys)
        ansible_interface.sync_authorized_key(ip, 'user={{ ansible_ssh_user }} key="%s" exclusive=True state=present' % keys)
        result = ansible_interface._get_result()
        if ip not in (list(set(result['host_unreachable'].keys() + result['host_ok'].keys() + result['host_failed'].keys()))):
            result['host_failed'][ip] = "sync failed, mabe password error"
        return json.dumps(result)

    except Exception:
        try:
            ip = keys_synv_info[0]
        except:
            ip = None
        _logger.error("sync failed:  %s" % traceback.format_exc())
        return json.dumps({
            'host_ok': '',
            'host_unreachable': '',
            'host_failed': {ip: "failed: %s" % traceback.format_exc()}
        })


@csrf_exempt
def sync_auth(request):
    '''
    同步用户key到服务器
    :param modules:
    :return:
    '''
    try:
        keys_synv_info = get_keys_sync_info() #根据需要同步的模块去查询每个ip对应要加的key
        #print keys_synv_info
        if not keys_synv_info or len(keys_synv_info) == 0:
            return HttpResponse({'result': "没有相关ip,或key获取失败，请检查日志"})
        # 定义并发runlist

        # 开始并发处理
        keys_sync_handler = my_concurrent.MyMultiProcess(10)
        #sync_auth_keys(keys_synv_info)
        for i in keys_synv_info:
            keys_sync_handler.multi_process_add(sync_auth_keys, i)
        keys_sync_handler.multi_process_wait()
        result = keys_sync_handler.get_result()

        g_res = dict()
        for _res in result:
            __res = json.loads(_res.get())
            for k,v in __res.items():
                if not g_res.has_key(k):
                    g_res[k] = dict()
                if v:
                    for _ip,r in v.items():
                        if _ip not in g_res[k].keys():
                            g_res[k][_ip] = []
                        g_res[k][_ip].append(r)

        # 设置用户已同步
        change_user_stat(status='synced')
    except(Exception):
        _logger.error(traceback.format_exc())
        g_res = "sync failed"
        return HttpResponse(json.dumps({'result': 'failed', 'info': g_res}))
    if g_res['host_failed'] or g_res['host_unreachable']:
        failed_ip = g_res['host_failed'].keys() + g_res['host_unreachable'].keys()
        return HttpResponse(json.dumps({'result': 'failed', 'info': '失败IP: %s' % failed_ip}))
    return HttpResponse(json.dumps({'result': 'success', 'info': '同步成功'}))

@csrf_exempt
def delete_user_auth(request):
    '''
    清除用户登陆
    :param request:
    :return:
    '''
    try:
        user_auth_name = request.POST.get('delete_user_name', 'None')
        CmdbUserSshAuth.objects.filter(username=user_auth_name).delete()
        return HttpResponse(json.dumps({'result': 'success','info':'用户key已删除，请点击同步'}))
    except Exception:
        _logger.error("delete_user_auth:%s" % traceback.format_exc())
        return HttpResponse(json.dumps({'result': 'failed', 'info':'删除失败'}))

@csrf_exempt
def get_user_info(request):
    '''
    展示所有用户信息
    :param request:
    :return:
    '''
    user_key_auth = datefield_to_str(list(CmdbUserSshAuth.objects.all().values()))
    return HttpResponse(json.dumps({"result":"success", "data": {"user_key_auth": user_key_auth,
                                    "nodes": get_all_node()}}))

@csrf_exempt
def tree_node_list(request):
    tree_node = datefield_to_str(list(CmdbTreeNode.objects.filter(depth=1,father_id=0).values()))
    return HttpResponse(json.dumps({"result": "success", "data": tree_node}))

@csrf_exempt
def commit_user_auth(request):
    UserAuthInfo, created = CmdbUserSshAuth.objects.get_or_create(username=request.POST.get('username'))
    UserAuthInfo.username = request.POST.get('username')
    UserAuthInfo.user_key = request.POST.get('user_key')
    UserAuthInfo.related_node = request.POST.get('related_node_selected')
    UserAuthInfo.status = request.POST.get('status')
    if created:
        UserAuthInfo.create_time = timezone.make_aware(datetime.datetime.strptime("02/03/2014 12:00 UTC", "%d/%m/%Y %H:%M %Z"), \
                                  timezone.get_default_timezone())
    UserAuthInfo.update_time = timezone.make_aware(datetime.datetime.strptime("02/03/2014 12:00 UTC", "%d/%m/%Y %H:%M %Z"), \
                                  timezone.get_default_timezone())
    UserAuthInfo.special_ip = request.POST.get('special_ip')

    UserAuthInfo.save()
    return HttpResponse(json.dumps({"result": "success", "info": "提交成功"}))