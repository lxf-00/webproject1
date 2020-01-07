from django.conf.urls import url
from cart.views import CartInfoView, CartAddView, CartUpdateView, CartDeleteView


# 配置URL和views（路由）
urlpatterns = [
    url(r'^$', CartInfoView.as_view(), name='cart_info'),   # 购物车
    url(r'^add$', CartAddView.as_view(), name='add'),       # 添加购物车
    url(r'^update$', CartUpdateView.as_view(), name='update'),  # 购物车更新
    url(r'^delete$', CartDeleteView.as_view(), name='delete'),  # 删除购物车记录
]