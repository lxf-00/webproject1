from django.conf.urls import url
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, OrderCommentView

# 配置URL和views（路由）
urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),   # 提交订单页面显示
    url(r'^commit$', OrderCommitView.as_view(), name='commit'), # 创建订单
    url(r'^pay$', OrderPayView.as_view(), name='pay'),      # 订单支付
    url(r'^check$', OrderCheckView.as_view(), name='check'),  # 支付结果查询
    url(r'^comment/(?P<order_id>\d+)$', OrderCommentView.as_view(), name='comment'),  # 订单评论
]