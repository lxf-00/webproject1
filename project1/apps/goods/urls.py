from django.conf.urls import url
from goods.views import IndexView


# 配置URL和views（路由）
urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),   # 首页
]