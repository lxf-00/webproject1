from django.contrib.auth.decorators import login_required   # 限制登录访问


class LoginRequiredMinix(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用父类的as_view方法
        view = super(LoginRequiredMinix, cls).as_view(**initkwargs)
        return login_required(view)

# UserInfoView 是LoginRequiredMinix 和view子类
# UserInfoView.as_view()