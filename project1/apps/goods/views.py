from django.shortcuts import render
from django.views.generic import View

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# Create your views here.

class IndexView(View):
    """视图类--首页"""

    def get(self, request):
        # 显示首页
        # 获取商品的种类信息
        types = GoodsType.objects.all()

        # 获取首页轮播商品信息
        goods_banners = IndexGoodsBanner.objects.all()

        # 获取促销活动商品信息
        promotion_banners = IndexPromotionBanner.objects.all()

        # 获取首页商品分类展示信息
        goods = IndexTypeGoodsBanner.objects.all()


        context = {
            'types': types,
        }

        return render(request, 'index.html', context)
