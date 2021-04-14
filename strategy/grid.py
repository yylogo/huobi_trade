# -*- coding:utf-8 -*-
# 策略实现
from datetime import datetime
import time
import numpy as np
# import ui_thread
import pandas as pd
import talib
import numpy as np
import math


STATE_WAITING_BUY = 0
STATE_CHECK_BUY = 1
STATE_WAITING_SELL = 2


class MyStrategy:

    def __init__(self, market):
        """ 初始化
        """
        self.klines = None
        self.last_macd_bar_val = -1

        self.status = STATE_WAITING_BUY
        self.start_check_time = -1

        # 1.5秒执行1次
        LoopRunTask.register(self.on_update_data_ticker, 0.1)

    async def on_update_data_ticker(self, *args, **kwargs):
        """ 定时执行任务
        """
        ori_data, _ = await self._rest_api.get_klines(self.symbol, '5min', sfrom=int(time.time() - 3600 * 5), to=int(time.time()))
        if not ori_data:
            logger.info("ori data is None: %r", ori_data)
            return
        data = ori_data['data']
        for info in data:
            info['time'] = datetime.fromtimestamp(int(info['id'])).now()
            del info['id']
        self.klines = data
        df_stockload = pd.DataFrame(self.klines)
        await self.on_ticker()

    async def on_ticker(self, *args, **kwargs):
        return

        if self.status == STATE_WAITING_BUY:
            await self.WaitToBuy()
        elif self.status == STATE_CHECK_BUY:
            self.CheckBuy()
        elif self.status == STATE_WAITING_SELL:
            await self.WaitToSell()

    # 判断是否购买成功
    def CheckBuy(self):
        if not self.trader.position:
            return
        if self.trader.position.long_quantity or self.trader.position.short_quantity or time.time() - self.start_check_time > 15:
            self.status = STATE_WAITING_SELL
            logger.info("[STATE] change to ", self.status)
        else:
            logger.info("[Check][Wait] Wait buy")
    
    # 等待时机购买
    async def WaitToBuy(self):
        if not self.klines or self.ask1_price == 0:
            return
        if not self.trader.assets or not self.trader.assets.assets.get(self.raw_symbol):
            return
        if self.macd_bar is None:
            return

        if self.macd_bar[-2] * self.macd_bar[-3] < 0 and self.macd_bar[-1] * self.macd_bar[-2] >= 0:
            if self.macd_bar[-2] > 0:
                # 买多
                price = self.ask1_price
                volume = math.floor(float(self.trader.assets.assets.get(self.raw_symbol).get("free")) * self.level * price // self.face_value)
                if volume <= 0:
                    logger.info("[Err][Buy] Can't buy! ")
                    return
                quantity = volume
                direction = 1
                logger.info("[OP][Buy] direction=up, price=%r, quantity=%r" % (price, quantity))
                order_id, err = await self.trader.create_order('BUY', str(price), int(quantity), lever_rate=self.level)
            else:
                price = self.bid1_price
                volume = math.floor(float(self.trader.assets.assets.get(self.raw_symbol).get("free")) * self.level * price // self.face_value)
                if volume <= 0:
                    logger.info("[Err][Buy] Can't buy! ")
                    return
                # 买空
                direction = -1
                quantity = -volume
                logger.info("[OP][Buy] direction=down, price=%r, quantity=%r" % (price, quantity))
                order_id, err = await self.trader.create_order('SELL', str(price), int(quantity), lever_rate=self.level)
            if err is None and order_id:
                self.status = STATE_CHECK_BUY
                self.start_check_time = time.time()
                logger.info("[STATE] change to ", self.status)
            logger.info("[RET][Buy] order_id=%r, err=%r" % (order_id, err))

    async def WaitToSell(self):
        if not self.trader.position:
            return
        if self.macd_bar is None:
            return

        if self.trader.orders:
            del_orders = []
            for order_id in self.trader.orders:
                if self.trader.orders[order_id].trade_type in [3, 4]:
                    del_orders.append(order_id)

            if del_orders:
                logger.info("[OP][Cancel] cancel order=%r" % (del_orders, ))
                _, error = await self.trader.revoke_order(*del_orders)
                if error:
                    return

        position = self.trader.position
        if position.long_quantity == 0 and position.short_quantity == 0:
            del_orders = self.trader.orders.keys()
            if del_orders:
                logger.info("[OP][Cancel] status ready to change, cancel order=%r" % (del_orders, ))
                _, error = await self.trader.revoke_order(*del_orders)
                if error:
                    return

            self.status = STATE_WAITING_BUY
            logger.info("[STATE] change to ", self.status)
            return

        if position.long_quantity:
            buy_price = position.long_avg_price
            win_rate = 100 * self.level * (self.bid1_price - buy_price) / buy_price
            sail_num = 0

            if win_rate < -9:
                sail_num = position.long_quantity
            elif self.macd_bar[-1] < self.macd_bar[-2] and self.macd_bar[-2] < self.macd_bar[-3] and win_rate >= 1:
                sail_num = position.long_quantity

            if sail_num:
                order_id, err = await self.trader.create_order('SELL', self.bid1_price, position.long_quantity, lever_rate=self.level)
                logger.info("[OP][SELL] direction=up, price=%r, quantity=%r, err=%r, order_id=%r" % (self.bid1_price, position.long_quantity, err, order_id))
        if position.short_quantity:
            buy_price = position.short_avg_price
            win_rate = 100 * self.level * (buy_price - self.ask1_price) / buy_price
            sail_num = 0

            if win_rate < -9:
                sail_num = position.short_quantity
            elif self.macd_bar[-1] > self.macd_bar[-2] and self.macd_bar[-2] > self.macd_bar[-3] and win_rate >= 1:
                sail_num = position.short_quantity

            if sail_num:
                order_id, err = await self.trader.create_order('BUY', self.bid1_price, -position.short_quantity, lever_rate=self.level)
                logger.info("[OP][SELL] direction=down, price=%r, quantity=%r, err=%r, order_id=%r" % (self.bid1_price, -position.long_quantity, err, order_id))

