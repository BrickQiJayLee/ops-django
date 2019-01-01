# coding=utf-8


from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.sessions.models import Session
import json
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


def check_login(session_id):
    """
    比对数据库sessionid
    :param session_select:
    :param session_id:
    :return:
    """
    return session_id in [ str(Session.objects.first()) ]

@csrf_exempt
def user_login(request):
    user = authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
    if user is not None:
        if not user.is_active:
            request.session.set_expiry(3600*24)
            HttpResponse(json.dumps({"result": "success", "username": request.user.username,
                                     "session_id": request.session.session_key}))
        else:
            login(request, user)
            return HttpResponse(json.dumps({"result": "success", "username": request.user.username,
                                     "session_id": request.session.session_key}))
    else:
        return HttpResponse(json.dumps({"result": "failed", "info": "密码或用户名错误"}))

@csrf_exempt
def check_login(request):
    """
        检查是否登陆
        :param session_select:
        :param session_id:
        :return:
        """
    import datetime
    now = datetime.datetime.now()
    sessions = list(Session.objects.filter(expire_date__gt=now).values())
    sessions_list = [i['session_key'] for i in sessions]
    if request.META.get("HTTP_SESSIONID", None) in sessions_list:
        return True
    else:
        return False

@csrf_exempt
def user_logout(request):
    Session.objects.filter(session_key=request.META.get("HTTP_SESSIONID", '')).delete()
    return HttpResponse(json.dumps({"result":"success", "info": "退出成功"}))


class LoginRequireMiddleWare(object):
    """
    登陆中间件
    """
    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):
        # 判断是否需要忽略登陆
        ignore = False
        for prefix in settings.AUTH_FREE_URL_PREFIX:
            if request.path.startswith(prefix):
                ignore = True
                break
        if ignore is False and not check_login(request):
            # 未登陆且未授权免登陆
            return HttpResponse(json.dumps({"result":"needLogin"}))
        # 判断结束，正常请求
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """ automatically handle exception in get response """
        pass


