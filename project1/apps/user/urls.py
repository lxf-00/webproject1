from django.conf.urls import url
from user.views import LoginView, RegisterView, ActivateView


# 配置URL和views（路由）
urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),          # 注册页面url路由
    url(r'^login$', LoginView.as_view(), name="login"),                   # 登录页面url路由

    url(r'^activate/(?P<token>.*)', ActivateView.as_view(), name='activate'),     # 账户激活页面url
]