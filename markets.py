# -*— coding:utf-8 -*-

import time
from alpha.utils import logger
from alpha.config import config
from alpha.tasks import LoopRunTask, SingleTask
from market.huobi import HuobiMarket
from market.huobi_test import HuobiTestMarket


class Markets(object):
    def __init__(self):
        super().__init__()
        self.markets = []

    def MarketFactory(self, market_config, is_test):
        market_class = None
        if is_test:
            market_class = HuobiTestMarket
        elif market_config['platform'] in ['huobi_swap', 'huobi_future']:
            market_class = HuobiMarket
        logger.info('test: ', is_test, market_class)

        if not market_class:
            logger.error("Can't find market class for", market_config['platform'])
            exit()
        market = market_class(market_config)
        self.markets.append(market)
        return market


markets = Markets()

