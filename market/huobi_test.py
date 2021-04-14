# -*— coding:utf-8 -*-
import copy
import time
import datetime
import math
import random
import pandas as pd
import asyncio
from alpha.utils import logger
from six.moves import xrange, zip
import numpy as np
import strategies as ST
from market.huobi import HuobiMarket
from alpha.tasks import LoopRunTask, SingleTask
from alpha.order import Order
from alpha.asset import Asset
from alpha.position import Position
from alpha.quant import quant


IS_CLOSE = False

# 回测数据市场撒旦法
class HuobiTestMarket(object):
    def __init__(self, market_config):
        super().__init__()
        self.market_config = market_config
        self.market = HuobiMarket(market_config)
        self.trader = self.market.trader
        self.now_timeline = int(time.time() - (2) * 24 * 3600)
        # self.now_timeline = int(time.time() - 5.5 * 3600)
        # self.now_timeline = 1615917738

        self.init_timeline = self.now_timeline
        self.klines_data = {}
        self.asset_list = []
        self.op_time = []
        self.inited = False
        self.level = int(market_config['level'])
        self.face_value = self.market.face_value

        SingleTask.run(self.InitMarket)
        self.klines_idx = {}
        self.last_tick_time = -1
        self.last_minut_s = -1
        self.last_tick_data = dict()
        self.high_first = False

        self.position = Position()
        self.position.long_quantity = 0
        self.position.short_quantity = 0
        self.tot_fee = 0
        self.free_asset = 100
        self.deal_count = 0
        self.tot_asset = self.free_asset
        self.init_asset = self.free_asset

        self.ask1_price = 0  # 卖一价格
        self.bid1_price = 0  # 买一价格

    async def InitMarket(self):
        the_start_time = self.now_timeline - 6 * 3600
        for period, step in [('1min', 120000 - 60), ('5min', 600000 - 60 * 5), ('15min', 1800000 - 60 * 15), ]:
        # for period, step in [('1min', 120000 - 60)]:
            if period in self.klines_data:
                continue

            now_time = the_start_time
            self.klines_data[period] = []
            print("{} period data start inited".format(period), end='', flush=True)

            while now_time + step + 1 < time.time():
                data = await self.market.GetKLines(period, now_time, now_time + step + 1)
                if not data:
                    await asyncio.sleep(0.04)
                    continue
                if self.klines_data[period] and self.klines_data[period][-1]['id'] == data[0]['id']:
                    data.remove(data[0])
                self.klines_data[period].extend(data)
                now_time += step
                print("\r{} period data init process: {:.2f}%".format(period, 100 * (now_time - the_start_time) / (time.time() - the_start_time)), end='', flush=True)

            while 1:
                data = await self.market.GetKLines(period, now_time, time.time())
                if not data:
                    await asyncio.sleep(0.04)
                    continue
                if self.klines_data[period] and self.klines_data[period][-1]['id'] == data[0]['id']:
                    data.remove(data[0])
                self.klines_data[period].extend(data)
                print("\r{} period data init process: {:.2f}%, with {} data".format(period, 100, len(self.klines_data[period])), flush=True)
                break

            for idx in xrange(len(self.klines_data[period])):
                if self.klines_data[period][idx]['id'] >= self.now_timeline:
                    self.last_tick_data[period] = copy.copy(self.klines_data[period][idx - 1])
                    self.klines_idx[period] = idx - 1
                    break

        self.inited = True
        self.UpdateTick()

    def UpdateTick(self):
        if self.now_timeline >= time.time():
            self.CalResult()
            quant.stop()
            ST.IS_CLOSE = True
            return
        if self.now_timeline == self.init_timeline:
            print("\nhuobi test process: %.1f%%" % (0, ), end='', flush=True)

        if self.last_tick_time != ST.strategies.tick_count:
            # 每次测试tick的更新时间
            # self.now_timeline += 60
            COUNT = 3
            self.last_minut_s += 1
            if self.last_minut_s >= COUNT:
                self.last_minut_s = 0
                self.now_timeline += 60 - COUNT + 1
                self.high_first = random.choice([True, False])

            self.last_tick_time = ST.strategies.tick_count
            f = 100 * (self.now_timeline - self.init_timeline) / (time.time() - self.init_timeline)
            print("\rhuobi test process: %.1f%%" % (f, ), end='', flush=True)

            for period in self.klines_idx:
                for idx in xrange(self.klines_idx[period] - 1, len(self.klines_data[period])):
                    if self.klines_data[period][idx]['id'] >= self.now_timeline:
                        if idx - 1 != self.klines_idx[period]:
                            self.klines_data[period][self.klines_idx[period]] = self.last_tick_data[period]
                            self.klines_idx[period] = idx - 1
                            self.last_tick_data[period] = copy.copy(self.klines_data[period][idx - 1])
                            d = self.klines_data[period][idx - 1]
                            d['close'] = d['high'] = d['low'] = d['open']
                        break

            min_data = self.last_tick_data['1min']
            if self.last_minut_s == 0:
                price = min_data['open']
            elif self.last_minut_s == COUNT - 1:
                price = min_data['close']
            elif self.last_minut_s == COUNT - 2:
                price = min_data['high'] if self.high_first else min_data['low']
            elif self.last_minut_s == COUNT - 3:
                price = min_data['low'] if self.high_first else min_data['high']
            else:
                price = random.uniform(min_data['low'], min_data['high'])
            # price = random.uniform(min_data['low'], min_data['high'])

            for period in self.klines_idx:
                d = self.klines_data[period][self.klines_idx[period]]
                if price > d['high']:
                    d['high'] = price
                if price < d['low']:
                    d['low'] = price
                d['close'] = price

            self.ask1_price = price  # 卖一价格
            self.bid1_price = price - 0.001  # 买一价格

            self.UpdateTotAsset()
            if self.last_minut_s == COUNT - 1:
                dateArray = datetime.datetime.fromtimestamp(self.now_timeline)
                otherStyleTime = dateArray.strftime("%Y-%m-%d %H:%M:%S")
                self.asset_list.append({'asset': self.tot_asset,
                    'price': price,
                    'time': otherStyleTime,
                    'op': self.op_time,})
                self.op_time = []

    async def GerOrders(self):
        pass

    async def GetPosition(self):
        return self.position

    def FetchFreeAsset(self):
        return self.free_asset

    def FetchTotAsset(self):
        self.UpdateTotAsset()
        return self.tot_asset

    async def CheckOrderStatus(self, order_id):
        # TODO：判断是否购买成功
        pass

    async def Buy(self, price, quantity):
        price = float(price)
        if self.free_asset < 0:
            return
        can_buy = math.floor(float(self.free_asset) * self.level * price // self.face_value)
        if can_buy == 0:
            print("Can't buy 3")
            return
        quantity = int(quantity)

        if (quantity > 0 and price < self.ask1_price) or (quantity < 0 and price > self.bid1_price): 
            return

        if abs(quantity) > can_buy:
            return

        logger.info("[OP Buy]", price, quantity)
        self.op_time.append(('BUY', price))
        asset_diya = abs(quantity) / price / self.level * self.face_value

        fee = abs(quantity) * 0.0004 * self.face_value / price
        # print('quantity:', quantity, 'fee:', fee)
        self.tot_fee += fee
        self.free_asset -= asset_diya + fee
        if quantity > 0:
            self.position.long_quantity += int(quantity)
            self.position.long_avg_price = price
        else:
            self.position.short_quantity += int(abs(quantity))
            self.position.short_avg_price = price
        return quantity

    async def Sell(self, price, quantity):
        if quantity == 0:
            return
        if (quantity > 0 and price > self.bid1_price) or (quantity < 0 and price < self.ask1_price): 
            return
        quantity = int(quantity)

        self.UpdateTotAsset()
        add_asset = 0
        if quantity > 0:
            if self.position.long_quantity < quantity:
                logger.error("Can't be!")
                return
            self.position.long_quantity -= quantity
            buy_price = self.position.long_avg_price
            dire = 1
            add_asset = (1/buy_price - 1/price) * quantity * self.face_value
            if self.position.long_quantity:
                self.position.long_avg_price = 0
        else:
            if self.position.short_quantity < int(abs(quantity)):
                logger.error("Can't be!")
                return
            self.position.short_quantity += quantity
            buy_price = self.position.short_avg_price
            dire = -1
            add_asset += (1/price - 1/buy_price) * -quantity * self.face_value
            if self.position.short_quantity:
                self.position.short_avg_price = 0

        logger.info("[OP Sell]", price, quantity)
        self.deal_count += 1
        self.op_time.append((buy_price, price, dire, add_asset))
        fee = abs(quantity) * 0.0004 * self.face_value / price
        self.tot_fee += fee
        self.free_asset = self.tot_asset - fee
        return quantity

    def UpdateTotAsset(self):
        asset_recover = 0
        add_asset = 0
        price = self.ask1_price
        if self.position.long_quantity > 0:
            quantity = self.position.long_quantity
            buy_price = self.position.long_avg_price
            add_asset = (1/buy_price - 1/price) * quantity * self.face_value
            asset_recover = abs(quantity) / buy_price / self.level * self.face_value

        if self.position.short_quantity > 0:
            quantity = self.position.short_quantity
            buy_price = self.position.short_avg_price
            add_asset += (1/price - 1/buy_price) * quantity * self.face_value
            asset_recover += abs(quantity) / buy_price / self.level * self.face_value

        self.tot_asset = self.free_asset + asset_recover + add_asset

    def CalResult(self):
        self.UpdateTotAsset()
        init_array = datetime.datetime.fromtimestamp(self.init_timeline)
        init_time_str = init_array.strftime("%Y-%m-%d %H:%M:%S")
        now_array = datetime.datetime.fromtimestamp(self.now_timeline)
        now_time_str = now_array.strftime("%Y-%m-%d %H:%M:%S")
        f = 100 * (self.now_timeline - self.init_timeline) / (time.time() - self.init_timeline)

        print('\nStart time: ', init_time_str, self.init_timeline)
        if f < 100:
            print('End time: ', now_array, 'rate:%.3f%%' % (f, ))
        print("left:", self.tot_asset, 'fee:', self.tot_fee, 'deal count:', self.deal_count)
        save = pd.DataFrame(self.asset_list)
        save.to_csv("test.csv")
        self.Draw()
        return

    def Draw(self):
        return

    async def GetRecentKLine(self, period, time_long):
        self.UpdateTick()
        last_idx = self.klines_idx[period]
        ret = self.klines_data[period][last_idx - time_long + 1:last_idx + 1]
        return ret

    def Search(self, li, key, find_big=True):
        le = 0
        ri = len(li) - 1
        while le < ri:
            if not find_big and (le + ri) & 1:
                mid = (le + ri) // 2
            else:
                mid = (le + ri) // 2

            if mid == key:
                return mid

            if key < li[mid]['id']:
                ri = mid - 1
            else:
                le = mid + 1
        return le

    async def GetKLines(self, period, from_time, to_time=None):
        self.UpdateTick()
        if self.now_timeline >= time.time():
            return None
        if to_time is None:
            to_time = self.now_timeline

        l1 = self.Search(self.klines_data[period], from_time)
        l2 = self.Search(self.klines_data[period], to_time, False)

    def time(self):
        return self.now_timeline
