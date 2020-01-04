# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_address'),
        ('goods', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderGoods',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('creat_time', models.DateField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateField(verbose_name='更新时间', auto_now=True)),
                ('is_delete', models.BooleanField(verbose_name='删除标记', default=False)),
                ('count', models.IntegerField(verbose_name='商品数目', default=1)),
                ('price', models.DecimalField(verbose_name='商品价格', max_digits=10, decimal_places=2)),
                ('comment', models.CharField(verbose_name='评论', max_length=256, default='')),
            ],
            options={
                'verbose_name': '订单商品',
                'verbose_name_plural': '订单商品',
                'db_table': 'p1_order_goods',
            },
        ),
        migrations.CreateModel(
            name='OrderInfo',
            fields=[
                ('creat_time', models.DateField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateField(verbose_name='更新时间', auto_now=True)),
                ('is_delete', models.BooleanField(verbose_name='删除标记', default=False)),
                ('order_id', models.CharField(verbose_name='订单id', primary_key=True, max_length=128, serialize=False)),
                ('pay_method', models.SmallIntegerField(verbose_name='支付方式', default=3, choices=[(1, '货到付款'), (2, '微信支付'), (3, '支付宝'), (4, '银联支付')])),
                ('total_count', models.IntegerField(verbose_name='商品数量', default=1)),
                ('total_price', models.DecimalField(verbose_name='订单总价', max_digits=10, decimal_places=2)),
                ('transit_price', models.DecimalField(verbose_name='运费', max_digits=10, decimal_places=2)),
                ('order_status', models.SmallIntegerField(verbose_name='订单状态', default=1, choices=[(1, '待支付'), (2, '代发货'), (3, '待收货'), (4, '待评价'), (5, '已完成')])),
                ('trade_no', models.CharField(verbose_name='支付编号', max_length=128)),
                ('addr', models.ForeignKey(verbose_name='地址', to='user.Address')),
                ('user', models.ForeignKey(verbose_name='用户', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '订单',
                'verbose_name_plural': '订单',
                'db_table': 'p1_order_info',
            },
        ),
        migrations.AddField(
            model_name='ordergoods',
            name='order',
            field=models.ForeignKey(verbose_name='订单', to='order.OrderInfo'),
        ),
        migrations.AddField(
            model_name='ordergoods',
            name='sku',
            field=models.ForeignKey(verbose_name='商品', to='goods.GoodsSKU'),
        ),
    ]
