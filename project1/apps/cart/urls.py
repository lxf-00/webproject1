from django.conf.urls import url
from cart.views import CartInfoView, CartAddView


# 配置URL和views（路由）
urlpatterns = [
    url(r'^$', CartInfoView.as_view(), name='cart_info'),   # 购物车
    url(r'^add$', CartAddView.as_view(), name='add'),       # 添加购物车
]