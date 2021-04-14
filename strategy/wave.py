# -*- coding:utf-8 -*-
# 专吃波动
import math
import numpy as np
import pandas as pd
from alpha.utils import logger
from six.moves import xrange, zip
from alpha.tasks import LoopRunTask, SingleTask

WAIT_TO_BUY = 0
WAIT_TO_DEAL = 2
WAIT_TO_SELL = 1


STATUS_DICT = {
        WAIT_TO_BUY: 'wait to buy',
        WAIT_TO_SELL: 'wait to sell',
        WAIT_TO_DEAL: 'wait to deal',
        }

class MyStrategy:
    def __init__(self, market):
        self.market = market
        self.status = WAIT_TO_BUY
        logger.info('[Status] init to', STATUS_DICT[self.status])

    async def Tick(self, *args, **kwargs):
        await self.CalWaveRange()
        position = await self.market.GetPosition()
        if position.short_quantity or position.long_quantity:
            await self.WaitSell()
        else:
            await self.WaitBuy()

    async def CalWaveRange(self):
        # TODO: 通过起始指针确定震荡区间，每次检查区间是否破开，区间的破开应该要考虑两个因素
        # 1. 新增的K线收盘超出范围
        # 2. 长度需要一个衰减，超过某个值
        pass

    async def WaitSell(self):
        if self.market.bid1_price <= 0:
            return
        min15_data = await self.market.GetRecentKLine('5min', 20)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        ratio = 100 * abs(self.market.face_value * (Ma3[-1] - Ma8[-1]) / max(Ma8[-1], Ma3[-1]))
        ma3_diff = 100 * abs(self.market.face_value * (Ma3[-1] - Ma3[-2]) / max(Ma3[-1], Ma3[-2]))
        direction = 0
        if (Ma3[-1] < Ma3[-2] and ma3_diff > 0.21) or (Ma3[-1] < Ma8[-1] and ratio > 0.4):
            direction = -1
        elif (Ma3[-1] > Ma3[-2] and ma3_diff > 0.21) or (Ma3[-1] > Ma8[-1] and ratio > 0.4):
            direction = 1

        position = await self.market.GetPosition()
        if position.long_quantity == 0 and position.short_quantity == 0:
            self.status = WAIT_TO_BUY
            logger.info('[Status] change to', STATUS_DICT[self.status])
            return

        sell_price = 0
        sell_num = 0
        win_rate = 0
        if position.long_quantity and position.long_quantity > 0:
            buy_price = position.long_avg_price
            win_rate = 100 * self.market.level * (self.market.bid1_price - buy_price) / buy_price
            if direction == -1:
                sell_price = self.market.bid1_price
                sell_num = position.long_quantity
        elif position.short_quantity and position.short_quantity > 0:
            buy_price = position.short_avg_price
            win_rate = 100 * self.market.level * (buy_price - self.market.ask1_price) / buy_price
            if direction == 1:
                sell_price = self.market.ask1_price
                sell_num = -position.short_quantity

        if sell_price == 0:
            return

        if sell_price != 0:
            order_id = await self.market.Sell(sell_price, sell_num)
            if order_id:
                logger.info("[Sell]", sell_price, sell_num, 'win rate: %.2f%%' % (win_rate, ))
            else:
                logger.info("[Sell] failed!")

    async def WaitBuy(self):
        if self.market.bid1_price <= 0:
            return
        min15_data = await self.market.GetRecentKLine('5min', 20)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        mark = 0
        ratio = 100 * abs(self.market.face_value * (Ma3[-1] - Ma8[-1]) / Ma8[-1])
        price = 0
        if (Ma3[-1] - Ma8[-1]) * (Ma3[-2] - Ma8[-2]) <= 0:
            if Ma3[-1] > Ma8[-1]:
                price = self.market.ask1_price
                mark = 1
            else:
                price = self.market.bid1_price
                mark = -1
        if mark == 0:
            return

        quantity = math.floor(float(free_asset) * self.market.level * price // self.market.face_value)
        if quantity == 0:
            return

        free_asset = self.market.FetchFreeAsset()
        tot_asset = self.market.FetchTotAsset()
        order_id = await self.market.Buy(price, quantity * mark)
        if not order_id:
            logger.info("[Buy] Failed!!")
            return
        logger.info("[Buy]", price, quantity * mark, tot_asset)


