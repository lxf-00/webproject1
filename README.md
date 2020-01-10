# 电商网站： 天天生鲜

## 模块及对应的版本：vesions
- 主要 main models/frames:
  - django(1.8.1),
  - Python3.6.8,
  - Redis(2.10.6),
  - pymysql(0.9.3),
  - celery(4.1.1),
  - py3Fdfs(2.2.0)
- 其他的详见文件中requirements.txt more other details, found out in 'requirements.txt' file inside.

## 主要功能实现： apps or functions
- 用户模块（user)
  - 注册登录页的实现:
    - orm对象操作数据库(django的用户认证系统及其他)；
    - 类视图（django.views.generic.View)；
    - redis实现用户（历史浏览）数据的缓存 list；
    - celery + redis 实现异步发送注册邮件；    
  - 用户页面（信息，订单，地址）：
    - Login_required（实现限制登录访问）
    - 模块语言（传递参数）
- 商品模块（goods)
  - 首页的展现：
    - fastdfs + nginx 实现图片的保存与取用（重写django保存图片的方式Storage);
    - 页面静态化：celery + nginx + django admin模块实现更新数据，页面静态化，减少数据库访问量；
    - django.core.cache：数据缓存。
  - 购物车订单数量的展现：
    - redis 类型 hash (cart_user.id 2(商品id) 3（数量)）；
  - 商品列表页的实现
    - django.core.paginator. Paginator 对数据进行分页；
- 购物车模块
  - 前端js: 实现购物车商品数量的增加、减少、手动输入, 删除
  - 后端view: ajax post 实现购物车对应商品数量的更新和删除购物车记录；
- 订单模块
  - 订单页面的显示（ajax post 购物车模块传递相关参数）
  - 订单创建（使用mysql事务， 悲观锁，乐观锁解决并发问题）；
  - 订单的支付、支付确认： alipay 支付接口api的使用（沙箱）；订单状态的变更；
  - 订单评价页面的实现

- 网站部署
  - uwsgi 服务器的配置与负载均衡；
  - nginx --> uwsgi ---> django  ---> mysql,redis,fastdfs,nginx; 使用nginx实现静态资源和动态资源的分别处理；
  
- 全文搜索框架： django-haystact + whoosh + jieba (稍有不足)
