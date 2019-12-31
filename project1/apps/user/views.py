from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse     # 反向解析
from django.http import HttpResponse
from django.views.generic import View            # 类视图
from django.contrib.auth import authenticate     # 用户信息校验
from django.conf import settings
from django.core.mail import send_mail

from user.models import User

from itsdangerous import TimedJSONWebSignatureSerializer as Serial    # 用于用户身份信息加密
from itsdangerous import SignatureExpired                             # 检测链接是否过期

import re

from celery_tasks.activate import send_activating_mail                # 导入发送邮件模块（celery处理过的）

# Create your views here.
# 实现用户注册页面的视图：视图类

class RegisterView(View):
    """视图类---注册页面"""

    def get(self, request):
        # get -- 显示注册页面
        return render(request, 'register.html')

    def post(self, request):
        # post --- 注册处理

        # 1, 接收用户数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get("allow")

        # 2, 检验数据真实性
        if not all([username, password, cpwd, email, allow]):
            return render(request, 'register.html', {'errmsg': "数据不完整...."})


        # 检验两侧密码是否一致
        if password != cpwd:
            return render(request, 'register.html', {'errmsg': "两次密码不一致....."})

        # 校验邮箱合法性
        if not re.findall(r'^[a-zA-Z0-9]+[a-zA-Z0-9_]+@[A-Za-z0-9]+\.com$', email):
            return render(request, 'register.html', {'errmsg':'邮箱格式不正确....'})

        # 校验是否同意了协议
        if not allow:
            return render(request, 'register.html', {'errmsg':'使用本网站，需要同意网站协议！'})

        # 校验用户是否存在
        try:
            user = User.objects.get(username=username)  # get查找不到会报错
        except User.DoesNotExist:
            user = None                                 # 报错表示用户名不存在

        if user:
            # 表示用户已存在
            return render(request, 'register.html', {'errmsg':'用户名已存在'})

        # 3, 进行业务处理： 注册
        # 利用create_users函数创建新的用户
        user = User.objects.create_user(username, email, password)
        # 激活标志
        user.is_active = 0
        # 提交数据库
        user.save()

        # 发送邮件进行用户激活: http:127.0.0.1:8000/user/activate/user_id
        # 加密用户的身份信息
        secret_key = settings.SECRET_KEY
        serial = Serial(secret_key, 3600)
        info = {"confirm": user.id}
        token = serial.dumps(info)  # bytes 类型 需要解码成str,不然运行会报错：bytes no Json serizable.....
        token = token.decode()
        # print(token)

        send_activating_mail.delay(email, username, token)    # celery 异步处理发送激活邮件


        # 最终返回到首页
        return redirect(reverse('goods:index'))


class ActivateView(View):
    """处理激活逻辑"""
    def get(self, request, token):
        serial = Serial(settings.SECRET_KEY, 3600)
        try:
            info = serial.loads(token)
            uid = info.get('confirm')
            user = User.objects.get(id=uid)
            user.is_active = 1
            user.save()

            return redirect(reverse('user:login'))
        except SignatureExpired:
            return HttpResponse("链接已过期....")









class LoginView(View):
    """"视图类--登录页面"""

    def get(self, request):
        # get方式显示登录页面
        return redirect(reverse('goods:index'))

    def post(self, request):
        # post方式执登录
        # 1， 接收数据
        username = request.POST.get("username")
        password = request.POST.get("password")

        # 2, 校验数据
        # 检验数据完整性
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': "数据不完整，请重新输入！"})

        # 3, 业务处理：登录
        # 校验用户名和密码是否正确
        user = authenticate(username=username, password=password)

        if user:
            # 代表user不为None,用户名和密码争取
            return HttpResponse("欢迎登录！")
        else:
            return render(request, 'login.html', {'errmsg':"密码或账号错误,请查证后在登录"})

