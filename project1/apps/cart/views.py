from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View
from utils.mixin import LoginRequiredMinix
from django_redis import get_redis_connection
from django.http import JsonResponse

from goods.models import GoodsSKU

# Create your views here.

# /cart/
class CartInfoView(LoginRequiredMinix, View):
    """视图类---购物车"""

    def get(self, request):
        # 显示购物车页面

        # 获取登录用户
        user = request.user
        # 获取用户购物车中商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        cart_dict = conn.hgetall(cart_key)

        """
        cart_dict 字典格式： {b'2': b'3', b'4': b'5'}
        cart_dict.items() 列表（键，值）格式： [(b'2', b'3'), (b'4', b'5')]
        """
        # {'商品id':商品数量}
        skus = []
        # 保存用户购物车中商品的总数目和总价格
        total_count = 0
        total_price = 0
        # 遍历获取商品的信息
        for sku_id, count in cart_dict.items():
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品小计
            amount = sku.price * int(count)
            # 动态给sku增加一个amount属性，保存商品小计
            sku.amount = amount
            # 动态给sku增加count属性，保存对应商品数量
            sku.count = count
            # 添加
            skus.append(sku)

            # 累加计算商品的总数目和总价格
            total_count += int(count)
            total_price += amount


        # 组织模板上下文
        context = {
            'total_price': total_price,
            'total_count': total_count,
            'skus': skus
        }

        return render(request, 'cart.html', context)



# 添加商品到购物车:
# 1）请求方式，采用ajax post
# 如果涉及到数据的修改(新增，更新，删除), 采用post
# 如果只涉及到数据的获取，采用get
# 2) 传递参数: 商品id(sku_id) 商品数量(count)

# ajax发起的请求都在后台，在浏览器中看不到效果
# cart/add
class CartAddView(View):
    """购物车添加视图类"""
    def post(self, request):
        # 添加购物车
        user = request.user

        if not user.is_authenticated():
            # 用户未登录
            return JsonResponse({'res':0, 'errmsg':'请先登录'})
        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 校验添加的数据
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg':'商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg':'商品不存在'})

        # 业务处理：添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # 先验证用户购物车中是否存在这一类商品，返回商品的数量
        # hget(cart_key, sku_id)
        cart_count = conn.hget(cart_key, sku_id)

        if cart_count:
            # 原先存在该商品,数量追加
            count += int(cart_count)

        # 检验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 代表新商品
        # hset sku_id 到cart_key中
        conn.hset(cart_key, sku_id, count)

        # 计算购物车中订单总数
        total_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '添加成功'})






