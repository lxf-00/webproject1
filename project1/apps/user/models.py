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

class Address(BaseModel):
    """地址模型类"""
    user = models.ForeignKey('User', verbose_name="所属账户")
    receiver = models.CharField(max_length=20, verbose_name="收件人")
    addr = models.CharField(max_length=256, verbose_name="收件地址")
    zip_code = models.CharField(max_length=6, verbose_name="邮政编码")
    phone = models.CharField(max_length=11, verbose_name="电话号码")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")

    class Meta:
        db_table = 'p1_address'
        verbose_name = '收件地址'
        verbose_name_plural = verbose_name