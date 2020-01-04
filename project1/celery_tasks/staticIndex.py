from celery import Celery
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

from django.template import loader
from django.conf import settings
import os

# worker 端：
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project1.settings")
# django.setup()


app = Celery('celery_tasks_staticIndex', broker=('redis://172.16.36.164:6379/2'))

# 静态页面的实现
@app.task
def generic_static_index():
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取促销活动商品信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by("index")

    # 获取首页商品分类展示信息
    for type in types:
        # 获取该种类下首页分类商品图片信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')

        # 获取该种类下首页分类商品文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type 增加属性
        type.image_banners = image_banners
        type.title_banners = title_banners

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 使用模板
    # 1, 加载模板文件， 返回模板对象
    temp = loader.get_template('static_index.html')

    # 2, 模板渲染
    static_index = temp.render(context)

    # 3, 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index)
