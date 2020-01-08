from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from user.views import LoginView, RegisterView, ActivateView, LogoutView, UserInfoView, OrderView, AddressView


# 配置URL和views（路由）
urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),          # 注册页面url路由
    url(r'^login$', LoginView.as_view(), name="login"),                   # 登录页面url路由

    url(r'^activate/(?P<token>.*)', ActivateView.as_view(), name='activate'),     # 账户激活页面url
    url(r'^logout$', LogoutView.as_view(), name='logout'),               # 注销url

    url(r'^$', UserInfoView.as_view(), name='user_info'),                      # 用户中心
    url(r'^order/(?P<page>\d+)$', OrderView.as_view(), name='user_order'),    # 用户订单页面
    url(r'^addr$', AddressView.as_view(), name='user_addr'),    # 用户地址


    # login_require 一般用法
    # url(r'^$', login_required(UserView.as_view(), login_url='user:login'), name='user'),
    # url(r'^addr$', login_required(AddressView.as_view(), login_url='user:login'), name='user_addr'),    # 用户地址

]