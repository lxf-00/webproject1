from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, Goods, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner


# Register your models here.

# 实现后台修改数据自动生成静态页面
# 重写admin.ModelAdmin中的save_model 和 delete_model方法

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """更新或新增表中的数据使用"""
        # 调用父类中的save_model方法
        super().save_model(request, obj, form, change)

        # 调用celery_tasks中的staticIndex任务重新生成新的静态首页
        from celery_tasks.staticIndex import generic_static_index
        generic_static_index.delay()

        # 清除原先首页的缓存, 使最新第一次访问可以从数据库中访问到最新的数据。
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除表中的数据使用"""
        # 调用父类中的delete_model方法
        super().save_model(request, obj)

        # 调用celery_tasks中的staticIndex任务重新生成新的静态首页
        from celery_tasks.staticIndex import generic_static_index
        generic_static_index.delay()

        # 清除原先首页的缓存, 使最新第一次访问可以从数据库中访问到最新的数据。
        cache.delete('index_page_data')




class GoodsTypeAdmin(BaseModelAdmin):
    pass

class GoodsSKUAdmin(BaseModelAdmin):
    pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass



admin.site.register(GoodsType, GoodsTypeAdmin),
admin.site.register(GoodsSKU, GoodsSKUAdmin),
admin.site.register(Goods),
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin),
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin),
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin),


