from django.conf.urls import url
from goods import views


# 配置URL和views（路由）
urlpatterns = [
    url(r'^index$', views.index, name='index')
]