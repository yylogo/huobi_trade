# -*— coding:utf-8 -*-
import time
import asyncio
from alpha.utils import logger
from six.moves import xrange, zip
from strategies import strategies

# 定义一下基本市场接口
# 市场：指包含单一货币资源的一系列接口和数据


class BaseMarket(object):
    def __init__(self, market_config):
        super().__init__()
        self.inited = True

    async def CheckTotCanBuy(self):
        pass

    async def FetchTotAsset(self):
        pass

    async def FetchFreeAsset(self):
        pass

    async def CheckOrderStatus(self, order_id):
        pass

    async def Buy(self, price, quantity):
        pass

    async def Sell(self, price, quantity):
        pass

    async def GetRecentKLine(self, period, time_long):
        pass

    async def GetKLines(self, period, from_time, to_time=None):
        pass

    async def CheckOrderStatus(self, order_id):
        pass
