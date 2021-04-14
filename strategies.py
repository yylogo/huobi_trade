# -*— coding:utf-8 -*-

import time
import asyncio
from alpha.utils import logger
from alpha.tasks import LoopRunTask, SingleTask

IS_CLOSE = False

class Strategies:
    def __init__(self):
        self.strategies_list = []
        self.is_test = False
        self.tick_count = 0

    def Init(self, global_args):
        self.is_test = global_args.test

    def Run(self):
        if self.is_test:
            SingleTask.run(self.Loop)
        else:
            LoopRunTask.register(self.Tick, 0.5)

    def CreateStrategy(self, market, market_config):
        try:
            for md_name in market_config['strategy_file']:
                module = __import__('strategy.' + md_name, globals(), locals(), [md_name])
                strategy_class = getattr(module, 'MyStrategy')
                self.strategies_list.append(strategy_class(market))
        except:
            logger.exception()
            logger.error("Create strategy failed")
            exit(0)

    async def Loop(self):
        start_time = time.time()
        while 1:
            if IS_CLOSE:
                return
            await self.Tick()
            if time.time() - start_time > 60 * 2:
                break
        SingleTask.run(self.Loop)

    async def Tick(self, *args, **argv):
        if not self.strategies_list:
            return
        self.tick_count += 1
        # TODO: 直接给所有的market加Tick
        for strategy in self.strategies_list:
            await strategy.Tick()


strategies = Strategies()

