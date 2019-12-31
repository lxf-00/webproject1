# celery 异步处理发送激活邮件
from celery import Celery
from django.core.mail import send_mail   # django 邮件发送系统
from django.conf import settings


# 实例化celery
# worker 端：
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project1.settings")
# django.setup()

app = Celery('celery_tasks_activate', broker=('redis://172.16.36.164:6379/9'))

# 任务逻辑实现
@app.task
def send_activating_mail(to_email, username, token):
    """
    send_mail(subject, message, from_email, recipient_list,
              fail_silently=False, auth_user=None, auth_password=None,
              connection=None, html_message=None):
    :return:
    """
    subject = '天天生鲜欢迎信息'
    message = ''                  # message 可以为空
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>'%(username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)   # 注意：html_message=html_message 必须这么写，记得在worker 上更正过来，不然会发送空白邮件