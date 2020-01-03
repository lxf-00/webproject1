# 实现fdfs 对图片的存储

from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client, get_tracker_conf          # 实现fdfs与python的交互



class FDFSStorage(Storage):
    """fast dfs 存储类"""

    def __init__(self, client_conf=None, base_url=None):
        # 初始化
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url


    def _open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def save(self, name, content):
        """保存文件时使用"""
        # name： 选择上传的文件名字
        # content: 包含上传文件内容的Field对象

        # 创建一个Fdfs_client对象
        path = get_tracker_conf(self.client_conf)
        client = Fdfs_client(path)

        # 上传文件到fast dfs系统中
        res = client.upload_appender_by_buffer(content.read())  # bytes类型

        """
         @return dict {
            'Group name'      : group_name,
            'Remote file_id'  : remote_file_id,
            'Status'          : 'Upload successed.',
            'Local file name' : '',
            'Uploaded size'   : upload_size,
            'Storage IP'      : storage_ip
        } if success else None
        """
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传fast dfs系统失败')

        # 获取file_id,并返回
        filename = res.get("Remote file_id")

        return filename

    def exists(self, name):
        """django 判断文件名是否可用"""
        return False

    def url(self, name):
        """返回访问文件的url路径"""
        return self.base_url + name





