from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse
from django.db import transaction     # django 使用事务
from django.conf import settings

import os

from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods

from utils.mixin import  LoginRequiredMinix

from datetime import datetime

from alipay import AliPay
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


# /order/pay
# 前段ajax post 提交：order_id(订单id)、
class OrderPayView(View):
    """订单支付"""
    def post(self, request):
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        # 校验订单是否有效

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user_id=user.id,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            # 订单不存在
            return JsonResponse({'res': 2, 'errmsg': '不存在该订单'})


        # 业务处理： 使用python sdk 调用支付宝的支付接口
        with open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')) as f:
            app_private_key = f.read()

        with open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')) as f:
            alipay_public_key = f.read()

        # 初始化
        alipay = AliPay(
            appid='2016102100731943', # 2016102100731943
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",   # RSA 或者 RSA2
            debug=True  # 默认False
        )



        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        # 沙箱环境跳转： https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price  # Decimal 不能被json 序列化
        print('total_pay', total_pay)
        print('order_id', order_id)
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,   # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject='天天生鲜%s' %order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


# /order/check
# ajax post 传递的参数： order_id
class OrderCheckView(View):
    """支付结果查询"""
    def post(self, request):
        # 用户登录校验
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录！'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        # 校验订单是否有效

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user_id=user.id,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            # 订单不存在
            return JsonResponse({'res': 2, 'errmsg': '不存在该订单'})


        # 业务处理： 使用python sdk 调用支付宝的支付接口
        with open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')) as f:
            app_private_key = f.read()

        with open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')) as f:
            alipay_public_key = f.read()

        # 初始化
        alipay = AliPay(
            appid='2016102100731943', # 2016102100731943
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",   # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            #         "trade_no": "2017032121001004070200176844",
            #         "code": "10000",
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #           {
            #             "amount": "20.00",
            #             "fund_channel": "ALIPAYACCOUNT"
            #           }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS",
            #         "total_amount": "20.00"
            #       }

            code = response.get('code')
            trade_status = response.get('trade_status')
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 代表支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4   # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'errmsg': "支付成功"})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                #  等待买家付款
                import time
                time.sleep(5)
                continue

            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


# /order/comment/order_id
class OrderCommentView(LoginRequiredMinix, View):
    def get(self, request, order_id):
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:user_order'))
        # 根据order_id 获取order_info
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:user_order'))

        # 获取订单商品
        order_skus = OrderGoods.objects.filter(order=order_id)

        # 遍历获取商品小计
        for order_sku in order_skus:
            amount = order_sku.price * order_sku.count
            # 动态增加属性
            order_sku.amount = amount

        # 给order 动态增加属性表示订单状态
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        # 动态增加属性，保存order_skus
        order.order_skus = order_skus

        # 返回应答
        return render(request, 'order_comment.html', {'order': order})






