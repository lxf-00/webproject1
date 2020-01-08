from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse     # 反向解析
from django.http import HttpResponse
from django.views.generic import View            # 类视图
from django.contrib.auth import authenticate, logout, login     # 用户信息校验, 注销, 记住登录状态
from django.conf import settings
from django_redis import get_redis_connection     # 导入django_redis实现用户浏览记录的缓存（需提前在setting中配置缓存设置）
from django.core.paginator import Paginator       # 分页

from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods

from itsdangerous import TimedJSONWebSignatureSerializer as Serial    # 用于用户身份信息加密
from itsdangerous import SignatureExpired                             # 检测链接是否过期

import re

from celery_tasks.activate import send_activating_mail                # 导入发送邮件模块（celery处理过的）
from utils.mixin import LoginRequiredMinix


# Create your views here.
# 实现用户注册页面的视图：视图类

# /user/register
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
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': "数据不完整...."})


        # 检验两侧密码是否一致
        if password != cpwd:
            return render(request, 'register.html', {'errmsg': "两次密码不一致....."})

        # 校验邮箱合法性
        if not re.findall(r'^[a-zA-Z0-9][a-zA-Z0-9_]+@[A-Za-z0-9]+\.com$', email):
            return render(request, 'register.html', {'errmsg':'邮箱格式不正确....'})

        # 校验是否同意了协议
        if allow != 'on':
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

        send_activating_mail.delay(email, username, token)    # celery 异步处理发送激活邮件


        # 最终返回到首页
        return redirect(reverse('goods:index'))


#/user/activate/token
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



# /user/login
class LoginView(View):
    """"视图类--登录页面"""

    def get(self, request):
        # get方式显示登录页面
        # request.user.is_authenticated() 判断用户是否已经登录
        if request.user.is_authenticated():
            # 代表已经登录，返回用户中心页面
            return redirect(reverse("user:user_info"))

        # 代表未登录,显示登录页面
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username=''
            checked=''

        # 使用模板
        return render(request, 'login.html', {'username':username, 'checked':'checked'})

    def post(self, request):
        # post方式执登录
        # 1， 接收数据
        username = request.POST.get("username")
        password = request.POST.get("pwd")

        # 2, 校验数据
        # 检验数据完整性
        if not all([username, password]):

            return render(request, 'login.html', {'errmsg':"数据不完整！"})

        # 3, 业务处理：登录
        # 校验用户名和密码是否正确
        user = authenticate(username=username, password=password)

        if user is not None:
            # 代表user不为None,用户名和密码正确
            # 判断是否为激活账户
            if user.is_active:
                # 代表是激活账户
                # 使用login 记录用户的登录状态
                login(request, user)
                response = redirect(reverse('user:user_info'))    # 实例化一个redirect对象，进行cookies设置

                # 判断用户是否需要记住用户名
                rem = request.POST.get("rem")

                if rem == 'on':
                    # 代表需要记住用户名
                    username = response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                return response

            else:
                return render(request, 'login.html', {'errmsg':'账户未激活，无法登录！'})
        else:
            return render(request, 'login.html', {'errmsg':"用户名或密码错误"})


# /user/logout
class LogoutView(View):
    """注销"""
    def get(self, request):
        # 退出登录，清除用户的session信息
        logout(request)

        # 返回首页
        return redirect(reverse('goods:index'))


# user
class UserInfoView(LoginRequiredMinix, View):
    """用户中心"""
    def get(self, request):
        # Django会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例对象
        # 如果用户登录->user是User类的一个实例对象
        # request.user.is_authenticated() 用于判断用户是否登录，如果登录返回Ture, 没有登录返回False

        # 获取登录对应的user
        # 获取相关的信息
        user = request.user
        address = Address.objects.get_default_address(user)

        # 获取用户历史浏览的历史记录
        # 使用Redis作为缓存： from redis import StrictRedis ===> sr = StrictRedis(host, port, db)
        # 使用django_redis: 先配置django缓存，之后: from django_redis import get_redis_connection

        conn = get_redis_connection('default')
        # 缓存的格式：使用list === history_23(用户id) [1, 3, 5] (商品id)

        history_key = 'history_%d'%user.id

        # 只保留最新的5个商品历史记录
        sku_id = conn.lrange(history_key, 0, 4)

        # 获取商品的具体信息
        goods_li = [GoodsSKU.objects.get(id=id) for id in sku_id]

        # 组织上下文
        context = {
            'page': 'user',
            'address':address,
            'goods_li':goods_li,
        }

        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件
        return render(request, 'user_center_info.html', context)


# user/order
class OrderView(LoginRequiredMinix, View):
    def get(self, request, page):
        # 获取登录用户
        user = request.POST.get('user')

        # 获取相关信息
        orders = OrderInfo.objects.filter(user=user)

        # 遍历
        for order in orders:
            # 根据order_id 查询订单商品
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus 获取商品小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price

                # 动态给order_sku 增加amount属性，保存小计
                order_sku.amount = amount

            # 动态给order增加属性，保存订单商品信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取该页的内容
        try:
            page = int(page)  # 将字符串类型的page转换为int
        except Exception as e:
            page = 1  # 报错显示第一页

        if page > paginator.num_pages:
            page = 1

        # 获取第page页d的Page实例对象
        order_page = paginator.page(page)

        # 进行页码控制：页面上最多显示5个页码
        # 1, 总页数小于5页，页面上显示所有页码
        # 2, 如果当前页是前三页，显示1-5页
        # 3, 如果当前页是后三页，显示后5页
        # 4, 其他情况，显示当前页的前2页，当前页， 当前页后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {
            'order_page': order_page,
            'pages': pages,
            'page': 'order'
        }

        return render(request, 'user_center_order.html', context)



# user/addr
class AddressView(LoginRequiredMinix, View):
    def get(self, request):
        # 获取登录user对应的user
        user = request.user

        # 获取默认地址
        address = Address.objects.get_default_address(user=user)

        return  render(request, 'user_center_site.html', {"page":'address', "address":address})

    def post(self, request):
        # 进行地址更新
        # 1，获取地址信息（来自用户）

        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 2， 校验数据
        # 校验数据的完整性
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg':'数据不完整！'})

        # 校验手机号
        if  not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg':'手机格式不正确'})

        # 3, 业务处理： 地址的添加
        # 如果用户存在默认地址，添加的地址不作为默认地址。反之，作为默认地址
        # 获取登录用户对应的User对象
        user = request.user

        # try:
        #     res_addr = Address.objects.get(user=user, is_default=1)
        # except Exception as e:
        #     # 不存在默认地址
        #     res_addr = None
        #

        # 运用模型管理器类实现获取默认地址方法
        address = Address.objects.get_default_address(user)

        if address:
            # 代表存在默认地址
            is_default = False
        else:
            # 不存在默认地址
            is_default = True

        # 添加地址
        Address.objects.create(user=user, receiver=receiver, addr=addr, zip_code=zip_code,
                               phone=phone, is_default=is_default)

        # 返回应答，刷新页面
        return redirect(reverse('user:user_addr'))





