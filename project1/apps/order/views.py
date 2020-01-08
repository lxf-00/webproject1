from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse
from django.db import transaction     # django 使用事务

from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods

from utils.mixin import  LoginRequiredMinix

from datetime import datetime
# Create your views here.

# /order/place
class OrderPlaceView(LoginRequiredMinix, View):
    """提交订单页显示"""
    def post(self, request):
        # 获取登录的用户
        user = request.user

        # 获取参数sku_ids
        sku_ids = request.POST.getlist('sku_ids')

        # 校验数据
        if not sku_ids:
            return redirect(reverse('cart:cart_info'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' %user.id


        skus = []
        # 保存商品的总价格和总件数
        total_count = 0
        total_price = 0
        # 遍历sku_ids，获取用户想要购买的商品id
        for sku_id in sku_ids:

            # 根据商品的id获取商品的相应信息
            sku = GoodsSKU.objects.get(id=sku_id)

            # 获取用户想要购买的商品数量
            count = conn.hget(cart_key, sku_id)

            # 计算商品的小计

            amount = sku.price * int(count)

            # 动态给sku增加属性
            sku.count = count
            sku.amount = amount

            # 添加
            skus.append(sku)

            # 累加件数和价格
            total_count += int(count)
            total_price += amount

        # 运费： 实际开发中有一个子系统
        transit_price = 10

        # 实付款
        total_pay = total_price + transit_price

        # 获取用户的收件地址
        addrs = Address.objects.filter(user=user)

        # 组织上下文
        sku_ids = ",".join(sku_ids)
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'sku_ids': sku_ids
        }

        # 使用模板
        return  render(request, 'place_order.html', context)


# order/commit
# 前段传递的参数：addr_id, sku_ids, pay_method
# 悲观锁
class OrderCommitView1(View):
    """订单"""
    @transaction.atomic
    def post(self, request):
        # 获取登录的用户
        user = request.user

        # 判断用户是否登录
        if not user.is_authenticated():
            # 未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收参数
        sku_ids = request.POST.get('sku_ids')
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        print(pay_method)

        # 校验参数
        if not all([sku_ids, addr_id, pay_method]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式是否存在
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 非法支付方式
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        # 判断地址是否存在
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址不存在'})

        # 业务处理： 订单创建

        # 组织参数
        # 订单id: 时间 + user.id == 202001081010+user.id
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总价格
        total_count = 0
        total_price = 0

        # 设置保存点
        save_id = transaction.savepoint()
        try:
            # 向p1_order_info中添加一条信息
            order = OrderInfo.objects.create(order_id=order_id,
                                     user=user,
                                     addr=addr,
                                     pay_method=pay_method,
                                     total_price=total_price,
                                     total_count=total_count,
                                     transit_price=transit_price)

            # 订单中有几个商品需要向订单商品表中添加几条信息： p1_order_goods
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品不存在
                try:
                    # 悲观锁 高并发
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 商品不存在
                    # 事务回滚save_id
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # 测试悲观锁
                print("user_id: %d, stock: %d" %(user.id, sku.stock))

                import time
                time.sleep(10)

                # 从redis中获取用户购买商品的数量
                count = conn.hget(cart_key, sku_id)

                # 判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # 向表中添加一条数据
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # 更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # 累加计算商品的总数量和总价格
                amount = sku.price * int(count)

                total_count += int(count)
                total_price += amount

            # 更新订单信息表中的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price

            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 业务提交
        transaction.savepoint_commit(save_id)

        # 清除用户购物车记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})

# 乐观锁
class OrderCommitView(View):
    """订单创建"""
    @transaction.atomic
    def post(self, request):
        # 获取登录的用户
        user = request.user

        # 判断用户是否登录
        if not user.is_authenticated():
            # 未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收参数
        sku_ids = request.POST.get('sku_ids')
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')

        # 校验参数
        if not all([sku_ids, addr_id, pay_method]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式是否存在
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 非法支付方式
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        # 判断地址是否存在
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址不存在'})

        # 业务处理： 订单创建

        # 组织参数
        # 订单id: 时间 + user.id == 202001081010+user.id
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总价格
        total_count = 0
        total_price = 0

        # 设置保存点
        save_id = transaction.savepoint()
        try:
            # 向p1_order_info中添加一条信息
            order = OrderInfo.objects.create(order_id=order_id,
                                     user=user,
                                     addr=addr,
                                     pay_method=pay_method,
                                     total_price=total_price,
                                     total_count=total_count,
                                     transit_price=transit_price)

            # 订单中有几个商品需要向订单商品表中添加几条信息： p1_order_goods
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品不存在
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        # 商品不存在
                        # 事务回滚save_id
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    # 从redis中获取用户购买商品的数量
                    count = conn.hget(cart_key, sku_id)

                    # 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 更新商品的库存和销量
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)


                    # # 测试乐观锁
                    # print("user.id: %d, times: %d, stock: %d" %(user.id, i, sku.stock))
                    #
                    # import time
                    # time.sleep(5)

                    res = GoodsSKU.objects.filter(id=sku.id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)


                    # update p1_goods_sku set stock=new_stock, sales = new_sales where id = sku.id stock=orgin_stock
                    # 返回受影响的行数
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败2'})
                        continue

                    # 向表中添加一条数据
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # 累加计算商品的总数量和总价格
                    amount = sku.price * int(count)

                    total_count += int(count)
                    total_price += amount

                    break

            # 更新订单信息表中的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price

            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败1'})

        # 业务提交
        transaction.savepoint_commit(save_id)

        # 清除用户购物车记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


