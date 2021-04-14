# -*- coding:utf-8 -*-
# 波动策略
import math
import time
import talib
import my_utils
import numpy as np
import pandas as pd
from datetime import datetime
from alpha.utils import logger
from six.moves import xrange, zip
from alpha.tasks import LoopRunTask, SingleTask


class MyStrategy:
    def __init__(self, market):
        """ 初始化
        """
        super().__init__()
        self.market = market

        self.price_model = None         # 接下来15分钟的价格模型
        self.start_check_time = -1

        import matplotlib.pyplot as plt

        plt.rcParams['font.sans-serif'] = ['SimHei'] #用来正常显示中文标签 
        plt.rcParams['axes.unicode_minus'] = False #用来正常显示负号 

    async def Tick(self, *args, **kwargs):
        """ 定时执行任务
        """
        min15_data = await self.market.GetRecentKLine('15min', 6)
        if not min15_data:
            logger.info("Can't fetch 15min data")
            return

        # 暂时不用min1 data
        # min1_data = await self.market.GetKLines('1min', min15_data[0]['id'])
        # if not min1_data:
            # return
        # for x in xrange(len(min1_data), 90):
            # min1_data.append(min1_data[-1])
            # min1_data[-1]['id'] += 60
            # min1_data[-1]['vol'] = 0
            # min1_data[-1]['amount'] = 0
            # min1_data[-1]['high'] = min1_data[-1]['low'] = min1_data[-1]['open'] = min1_data[-1]['close']
        # df_1min = pd.DataFrame(min1_data)

        df_15min = pd.DataFrame(min15_data)

        d = df_15min.open.values - df_15min.close.values
        for sidx in xrange(len(d)):
            if sidx <= 2:
                continue
            if d[sidx] * d[sidx - 1] > 0 and d[sidx - 1] * d[sidx - 2] > 0:
                z += 1
                df_std.loc[idx, 'open'] = -1
                df_std.loc[idx, 'close'] = -1
                df_std.loc[idx, 'low'] = -1
                return

        high_std = np.std(df_15min.high)
        low_std = np.std(df_15min.low)
        if high_std > 0.05 or low_std > 0.05:
            return

        average
        current_price = self.market.

        # 绘画部分

        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import mpl_finance as mpf

        # fig = self.show_windows
        fig = plt.figure(figsize=(20,12), dpi=88, facecolor="white") #创建fig对象
        gs = gridspec.GridSpec(4, 1, left=0.08, bottom=0.15, right=0.99, top=0.96, wspace=None, hspace=0, height_ratios=[2.5,2.5,1,1])
        graph_1 = fig.add_subplot(gs[0,:])
        graph_2 = fig.add_subplot(gs[1,:])
        graph_3 = fig.add_subplot(gs[2,:])
        graph_4 = fig.add_subplot(gs[3,:])

        my_utils.candlestick2_ohlc(graph_2, df_15min.open, df_15min.high, df_15min.low, df_15min.close, width=1, colorup='r', colordown='g')
        mpf.candlestick2_ochl(graph_1, df_1min.open, df_1min.close, df_1min.high, df_1min.low, width=1, colorup='r', colordown='g')
        plt.show()
        # fig.canvas.draw_idle()
        # fig.canvas.start_event_loop(0.05)

    async def Test(self):
        min15_data = await self.market.GetRecentKLine('15min', -1)

        import copy
        df_15min = pd.DataFrame(min15_data)
        # gstd = copy.deepcopy(min15_data)
        df_std = pd.DataFrame(copy.deepcopy(min15_data))
        Ma5 = df_15min.close.rolling(window=5).mean()
        z = 0
        for idx in xrange(len(df_std)):
            if idx <= 10:
                df_std.loc[idx, 'open'] = -1
                df_std.loc[idx, 'close'] = -1
                df_std.loc[idx, 'low'] = -1
                continue
            # d =  - df_15min.close[idx - 5:idx + 1]
            find = False
            d = df_15min[idx - 5:idx + 1].open.values - df_15min[idx - 5:idx + 1].close.values
            for sidx in xrange(len(d)):
                if sidx <= 2:
                    continue
                if d[sidx] * d[sidx - 1] > 0 and d[sidx - 1] * d[sidx - 2] > 0:
                    z += 1
                    df_std.loc[idx, 'open'] = -1
                    df_std.loc[idx, 'close'] = -1
                    df_std.loc[idx, 'low'] = -1
                    find = True
                    break
            if find:
                continue

            high_std = np.std(df_15min.high[idx - 5:idx + 1])
            low_std = np.std(df_15min.low[idx - 5:idx + 1])
            if high_std > 0.05 or low_std > 0.05:
                z += 1
                df_std.loc[idx, 'open'] = -1
                df_std.loc[idx, 'close'] = -1
                df_std.loc[idx, 'low'] = -1
                find = True
            if find:
                continue

            # ms = Ma5[idx - 6: idx + 1]
            # msdiff = ms.diff().mean()
            # if msdiff >= 0.003 or msdiff <= -0.03:
                # z += 1
                # df_std.loc[idx, 'open'] = -1
                # df_std.loc[idx, 'close'] = -1
                # df_std.loc[idx, 'low'] = -1

        logger.info("z", z, 'tot', len(df_std))

        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import mpl_finance as mpf

        # fig = self.show_windows
        fig = plt.figure(figsize=(20,12), dpi=88, facecolor="white") #创建fig对象
        gs = gridspec.GridSpec(4, 1, left=0.08, bottom=0.15, right=0.99, top=0.96, wspace=None, hspace=0, height_ratios=[2.5,2.5,1,1])
        graph_1 = fig.add_subplot(gs[0,:])
        graph_2 = fig.add_subplot(gs[1,:])
        graph_3 = fig.add_subplot(gs[2,:])
        graph_4 = fig.add_subplot(gs[3,:])
        my_utils.candlestick2_ohlc(graph_1, df_15min.open, df_15min.high, df_15min.low, df_15min.close, width=1, colorup='r', colordown='g')
        my_utils.draw_input(graph_1, df_std.open, df_std.high, df_std.low, df_std.close, width=1)
        plt.savefig('test.png')


