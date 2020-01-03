# 电商网站： webproject1

## 模块及对应的版本：vesions
- 主要 main models/frames: django(1.8.1), Python3.6.8, Redis(2.10.6), pymysql(0.9.3), celery(4.1.1), py3Fdfs(2.2.0)
- 其他的详见文件中requirements.txt more other details, found out in 'requirements.txt' file inside.

## 主要功能实现： apps or functions
- 用户模块（user)
  - 注册登录页的实现: orm对象操作数据库(django的用户认证系统及其他)；redis实现用户数据的缓存； celery redis 实现异步发送注册邮件；类视图（django.views.generic.View)；
  - 用户页面（信息，订单，地址）：Login_required（实现限制登录访问）,模块语言（传递参数）；
- 商品模块（goods)
  - 首页的展现： fastdfs + nginx 实现图片的保存与取用（重写django保存图片的方式Storage);
  - 购物车订单数量的展现： redis 类型 hash (cart_user.id 2(商品id) 3（数量)）；
