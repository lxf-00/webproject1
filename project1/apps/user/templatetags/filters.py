# 自定义过滤器：整型和浮点型数相加，不发生类型改变，保留两位小数
from django.template import Library

#  创建Libary类对象
register = Library()

@register.filter
def add_no_change(a, b):

    return a+b

