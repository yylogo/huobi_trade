# -*- coding:utf-8 -*-
# 波动策略
import math
import numpy as np
import pandas as pd
from alpha.utils import logger
from six.moves import xrange, zip
from alpha.tasks import LoopRunTask, SingleTask


class MyStrategy:
    def __init__(self, market):
        self.market = market

        self.need_win = 0

        self.status = 0
        self.now = 100
        logger.info('[Status] init to', self.status)

    async def Tick(self, *args, **kwargs):
        await self.market.GetRecentKLine('15min', 15)

        position = await self.market.GetPosition()
        if self.status in [0, 1] and (position.short_quantity or position.long_quantity):
            self.status = 2
            logger.info('[Status] change to', self.status)
        elif self.status == 2:
            if not position.short_quantity and not position.long_quantity:
                self.status = 0
                logger.info('[Status] change to', self.status)
                return

            await self.WaitSell()
        else:
            await self.WaitBuy()

    async def WaitSell(self):
        position = await self.market.GetPosition()
        if position.long_quantity == 0 and position.short_quantity == 0:
            self.status = 0
            logger.info('[Status] change to', self.status)
            return
        if position.long_quantity and position.long_quantity > 0:
            buy_price = position.long_avg_price
            win_rate = 100 * self.market.level * (self.market.bid1_price - buy_price) / buy_price
            if win_rate < -9 or win_rate > 2:
                await self.market.Sell(self.market.ask1_price, position.long_quantity)

        if position.short_quantity and position.short_quantity > 0:
            buy_price = position.short_avg_price
            win_rate = 100 * self.market.level * (buy_price - self.market.bid1_price) / buy_price
            if win_rate < -9 or win_rate > 2:
                await self.market.Sell(self.market.bid1_price, -position.short_quantity)

    async def WaitBuy(self):
        min15_data = await self.market.GetRecentKLine('15min', 15)
        if not min15_data:
            logger.info("Can't fetch 15min data")
            return

        df_15min = pd.DataFrame(min15_data)
        is_smooth = await self.CheckSmooth(df_15min)
        if is_smooth:
            await self.OperationTick(df_15min)

    async def CheckSmooth(self, ori_data):
        # 可以用多个指标来判断是否处于平稳的震荡期
        df_15min = ori_data[-6:-1]
        d = df_15min.open.values - df_15min.close.values
        for sidx in xrange(len(d)):
            if sidx <= 2:
                continue
            if d[sidx] * d[sidx - 1] > 0 and d[sidx - 1] * d[sidx - 2] > 0:
                return False

        high_std = np.std(df_15min.high)
        low_std = np.std(df_15min.low)
        if high_std > 0.05 or low_std > 0.05:
            return False
        return True

    async def OperationTick(self, ori_data):
        df_15min = ori_data[-6:-1]
        max_max = df_15min[-6:-1].high.max()
        min_min = df_15min[-6:-1].low.min()
        ave = (max_max + min_min) / 2

        price = self.market.ask1_price
        if abs(price - ave) / (max_max - min_min) * 2 > 0.8:
            self.need_win
            if price > ave:
                price = self.market.ask1_price
                mark = -1
            else:
                price = self.market.bid1_price
                mark = 1
            self.need_win = abs(0.8 * 100 * self.market.level * (ave - price) / price)
            free_asset = await self.market.FetchFreeAsset()
            quantity = math.floor(float(free_asset) * self.market.level * price // self.market.market.face_value)
            if quantity == 0:
                return
            await self.market.Buy(price, quantity * mark)
            self.status = 1
            logger.info('[Status] change to', self.status)

