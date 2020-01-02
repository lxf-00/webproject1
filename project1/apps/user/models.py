from django.db import models
from db.base_model import BaseModel
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser, BaseModel):
    """用户模型类"""


    class Meta:
        # 规定数据库中表的名字
        db_table = "p1_user"
        # 别称（单复数）
        verbose_name = "用户"
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    """地址模型类管理器"""
    # 1, 改变原有的查询结果
    # 2， 封装方法,用户操作模型类对应的数据库（增删改查）
    def get_default_address(self, user):
        # self.model 获取self所在的模型类
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            # 不存在默认收货地址
            address = None

        return address


class Address(BaseModel):
    """地址模型类"""
    user = models.ForeignKey('User', verbose_name="所属账户")
    receiver = models.CharField(max_length=20, verbose_name="收件人")
    addr = models.CharField(max_length=256, verbose_name="收件地址")
    zip_code = models.CharField(max_length=6, verbose_name="邮政编码")
    phone = models.CharField(max_length=11, verbose_name="电话号码")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")

    # 自定义一个模型管理类
    objects = AddressManager()

    class Meta:
        db_table = 'p1_address'
        verbose_name = '收件地址'
        verbose_name_plural = verbose_name