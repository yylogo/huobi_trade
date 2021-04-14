# -*- coding:utf-8 -*-
# 斜率
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
        min15_data = await self.market.GetRecentKLine('1min', 20)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        df_data.close.iloc[-1] = min15_data[-1]['low']
        Ma3 = list(df_data.close.rolling(window=LOW_WINDOW).mean())
        direction = 0
        if Ma3[-2] < Ma3[-3] and Ma3[-1] < Ma3[-2]:
            direction = -1

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
            if win_rate > 1 or win_rate < -1:
                sell_price = self.market.bid1_price
                sell_num = position.long_quantity
        elif position.short_quantity and position.short_quantity > 0:
            buy_price = position.short_avg_price
            win_rate = 100 * self.market.level * (buy_price - self.market.ask1_price) / buy_price
            if win_rate > 1 or win_rate < -1:
            # if direction == 1:
                sell_price = self.market.ask1_price
                sell_num = -position.short_quantity

        if sell_price == 0:
            return
        if self.last_sell_price == sell_price:
            return
        self.last_sell_price = sell_price

        if self.market.trader.orders:
            del_orders = []
            for order_id in self.market.trader.orders:
                if self.market.trader.orders[order_id].trade_type in [3, 4]:
                    del_orders.append(order_id)

            if del_orders:
                _, error = await self.market.trader.revoke_order(*del_orders)
                if error:
                    logger.error("[Cancel] cancel failed!", error)
                    return

        if sell_price != 0:
            await self.market.Sell(sell_price, sell_num)
            logger.info("[Sell]", sell_price, sell_num, 'win rate: %.2f%%' % (win_rate, ))

    async def WaitBuy(self):
        if self.market.bid1_price <= 0:
            return
        min15_data = await self.market.GetRecentKLine('1min', 30)
        if not min15_data:
            return

        df_data = pd.DataFrame(min15_data)
        # 判断买入
        Ma3 = list(df_data.close.rolling(window=LOW_WINDOW).mean())
        # 看多
        mark = 0
        price = 0
        if Ma3[-1] > Ma3[-2] and Ma3[-2] > Ma3[-3]:
            price = self.market.ask1_price
            if price < Ma3[-1] and price > min15_data[-1]['low']:
                mark = 1

        if price * mark == self.last_buy_price:
            return
        if mark == 0:
            return

        if self.market.trader.orders:
            del_orders = []
            for order_id in self.market.trader.orders:
                if self.market.trader.orders[order_id].trade_type in [1, 2]:
                    del_orders.append(order_id)

            if del_orders:
                _, error = await self.market.trader.revoke_order(*del_orders)
                if error:
                    logger.error("[Cancel] cancel failed!", error)
                    return
        free_asset = self.market.FetchFreeAsset()
        tot_asset = self.market.FetchTotAsset()
        self.last_buy_price = price * mark
        quantity = float(free_asset) * self.market.level * price // self.market.face_value
        quantity = math.floor(0.75 * quantity)
        print(quantity)
        if quantity == 0:
            return
        await self.market.Buy(price, quantity * mark)
        self.last_sell_price = 0
        logger.info("[Buy]", price, quantity * mark, tot_asset)

