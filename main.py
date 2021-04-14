# -*— coding:utf-8 -*-

import signal
import sys
import time
import argparse
from alpha.utils import logger
from alpha.config import config
from markets import markets
import strategies as ST
from alpha.quant import quant
from alpha.tasks import LoopRunTask, SingleTask

finished_set = set()
Last_Sig_Time = -1


async def CreateStratgies():
    global finished_set
    for market in markets.markets:
        if market.inited:
            market_config = market.market_config
            ST.strategies.CreateStrategy(market, market_config)
            finished_set.add(id(market))
            logger.info('-----', market, 'inited done..')
    if len(finished_set) != len(markets.markets):
        SingleTask.call_later(CreateStratgies, 0.1)
        return
    ST.strategies.Run()
    logger.info("Program init successs") 


def keyboard_interrupt(s, f):
    global Last_Sig_Time
    if time.time() - Last_Sig_Time < 2:
        Stop()
        return
    Last_Sig_Time = time.time()
    for market in markets.markets:
        if not market.inited:
            Stop()
            return
        ret = market.CalResult()
        if ret:
            Stop()
            return


def Stop():
    ST.IS_CLOSE = True
    quant.stop()


def main():
    parser = argparse.ArgumentParser(description='Process args.')   # 首先创建一个ArgumentParser对象
    parser.add_argument('-t', '--test', help='Not operate real account.', action='store_true')
    args = parser.parse_args()

    quant.initialize('config.json')
    ST.strategies.Init(args)

    logger.info("args", args, 'argss', sys.argv)
    signal.signal(signal.SIGINT, keyboard_interrupt)
    if args.test:
        logger.initLogger("ERROR")
        logger.info("run in test mode")
    else:
        logger.info("run in real mode")

    for market_config in config.MARKETS:
        markets.MarketFactory(market_config, args.test)
    SingleTask.run(CreateStratgies)

    quant.start()


if __name__ == '__main__':
    main()

