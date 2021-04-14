# -*- coding:utf-8 -*-
# 追涨杀跌
import math
import numpy as np
import pandas as pd
from alpha.utils import logger
from six.moves import xrange, zip
from alpha.tasks import LoopRunTask, SingleTask

LOW_WINDOW = 3
BIG_WINDOW = 9

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
        self.last_buy_price = 0
        self.last_sell_price = 0
        self.need_win = 10
        self.need_lose = 10
        logger.info('[Status] init to', STATUS_DICT[self.status])

    async def Tick(self, *args, **kwargs):
        position = await self.market.GetPosition()
        if position.short_quantity or position.long_quantity:
            if self.status != WAIT_TO_SELL:
                self.status = WAIT_TO_SELL
                logger.info('[Status] change to', STATUS_DICT[self.status])

        if self.status == WAIT_TO_SELL:
            await self.WaitSell()
        else:
            await self.WaitBuy()

    async def WaitSell(self):
        if self.market.bid1_price <= 0:
            return
        min15_data = await self.market.GetRecentKLine('15min', 20)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        Ma3 = list(df_data.close.rolling(window=LOW_WINDOW).mean())
        Ma8 = list(df_data.close.rolling(window=BIG_WINDOW).mean())
        ratio = 100 * abs(self.market.face_value * (Ma3[-1] - Ma8[-1]) / max(Ma8[-1], Ma3[-1]))
        ma3_diff = 100 * abs(self.market.face_value * (Ma3[-1] - Ma3[-2]) / max(Ma3[-1], Ma3[-2]))
        # if Ma3[-2] > Ma8[-2]:
        direction = 0
        if Ma3[-1] < Ma8[-1]:
            direction = -1
        elif Ma3[-1] > Ma8[-1]:
            direction = 1
        # if (Ma3[-1] < Ma3[-2] and ma3_diff > 0.21) or (Ma3[-1] < Ma8[-1] and ratio > 0.4):
            # direction = -1
        # elif (Ma3[-1] > Ma3[-2] and ma3_diff > 0.21) or (Ma3[-1] > Ma8[-1] and ratio > 0.4):
            # direction = 1

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
            if win_rate > self.need_win or win_rate < -self.need_lose:
            # if win_rate > self.need_win:
                sell_price = self.market.bid1_price
                sell_num = position.long_quantity
        elif position.short_quantity and position.short_quantity > 0:
            buy_price = position.short_avg_price
            win_rate = 100 * self.market.level * (buy_price - self.market.ask1_price) / buy_price
            # if win_rate > 2 or win_rate < -1:
            # if direction == 1:
            if win_rate > self.need_win or win_rate < -self.need_lose:
            # if win_rate > self.need_win:
                sell_price = self.market.ask1_price
                sell_num = -position.short_quantity

        if sell_price == 0:
            return
        if self.last_sell_price == sell_price:
            return
        self.last_sell_price = sell_price

        if sell_price != 0:
            order_id = await self.market.Sell(sell_price, sell_num)
            if order_id:
                logger.info("[Sell]", sell_price, sell_num, 'win rate: %.2f%%' % (win_rate, ))
            else:
                logger.info("[Sell] failed!")

    async def WaitBuy(self):
        if self.market.bid1_price <= 0:
            return
        min15_data = await self.market.GetRecentKLine('15min', 20)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        Ma3 = list(df_data.close.rolling(window=LOW_WINDOW).mean())
        Ma8 = list(df_data.close.rolling(window=BIG_WINDOW).mean())
        mark = 0
        ratio = 100 * abs(self.market.face_value * (Ma3[-1] - Ma8[-1]) / Ma8[-1])
        price = 0
        # if (Ma3[-3] - Ma8[-3]) * (Ma3[-2] - Ma8[-2]) <= 0:
        if (Ma3[-1] - Ma8[-1]) * (Ma3[-2] - Ma8[-2]) <= 0:
            if Ma3[-1] > Ma8[-1]:
                price = self.market.ask1_price
                mark = 1
            else:
                price = self.market.bid1_price
                mark = -1
        if price * mark == self.last_buy_price:
            return
        if mark == 0:
            return

        free_asset = self.market.FetchFreeAsset()
        quantity = float(free_asset) * self.market.level * price // self.market.face_value
        quantity = math.floor(quantity)
        quantity = math.floor(0.25 * quantity)
        if quantity == 0:
            return

        su = 0
        for x in range(1, 4):
            su += 10 * 100 * 0.5 * abs(df_data.high.iloc[-x] - df_data.low.iloc[-x]) / max(df_data.high.iloc[-x], df_data.low.iloc[-x])
        self.need_win = su / 3
        if self.need_win < 2:
            return
        # if self.need_win <= 6:
            # return
        # if self.need_win < 4:
            # quantity = math.floor(0.1 * quantity)
            # self.need_lose = 1 * self.need_win
        # elif self.need_win < 6:
            # quantity = math.floor(0.1 * quantity)
            # self.need_lose = 1.2 * self.need_win
        # else:
            # quantity = math.floor(0.25 * quantity)
            # self.need_lose = 1.2 * self.need_win
        # self.need_win = 5
        # self.need_lose = 10
        self.need_lose = 10 * self.need_win

        tot_asset = self.market.FetchTotAsset()
        order_id = await self.market.Buy(price, quantity * mark)
        if not order_id:
            logger.info("[Buy] Failed!!")
            return
        self.last_buy_price = price * mark
        self.last_sell_price = 0
        logger.info("[Buy]", price, quantity * mark, tot_asset)

