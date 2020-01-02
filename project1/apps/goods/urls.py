from django.conf.urls import url
from goods import views


# 配置URL和views（路由）
urlpatterns = [
    url(r'^$', views.index, name='index')
]