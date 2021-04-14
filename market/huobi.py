# -*— coding:utf-8 -*-
import time
from alpha.utils import logger
from alpha.utils import logger
from alpha.config import config
from alpha.market import Market
from alpha.trade import Trade
from alpha.orderbook import Orderbook
from alpha.kline import Kline
from alpha.markettrade import Trade as MarketTrade
from alpha.order import Order
from alpha.asset import Asset
from alpha.position import Position
from alpha.error import Error
from alpha.platforms.huobi_swap_api import HuobiSwapRestAPI
from alpha.platforms.huobi_future_api import HuobiFutureRestAPI
from alpha.order import ORDER_ACTION_SELL, ORDER_ACTION_BUY, ORDER_STATUS_FAILED, ORDER_STATUS_CANCELED, ORDER_STATUS_FILLED,\
    ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET


class HuobiMarket(object):
    def __init__(self, market_config):
        super().__init__()

        self.market_config = market_config
        self.symbol = market_config['symbol']
        self.api_symbol = market_config['symbol'].split('_')[0].split('-')[0]

        if market_config['platform'] == 'huobi_swap':
            self._rest_api = HuobiSwapRestAPI(market_config["host"], market_config["access_key"], market_config["secret_key"])
        elif market_config['platform'] == 'huobi_future':
            self._rest_api = HuobiFutureRestAPI(market_config["host"], market_config["access_key"], market_config["secret_key"])
            if market_config['contract_type'] == 'quarter':
                self.api_symbol += '_CQ'
        self.level = int(market_config['level'])
        if self.symbol in ['BTC-USD', 'BTC']:
            self.face_value = 100
        elif self.symbol in ['EOS-USD', 'EOS']:
            self.face_value = 10
        self.raw_symbol = self.symbol.split('_')[0] if market_config['contract_type'] != 'SWAP' else self.symbol.split('-')[0]
        channels = ["orderbook", "kline", "trade"]
        self.init_asset = 0

        # 交易模块
        cc = {
            "strategy": self.symbol,
            "platform": market_config["platform"],
            "symbol": self.symbol,
            "contract_type": market_config['contract_type'],
            "account": market_config["account"],
            "access_key": market_config["access_key"],
            "secret_key": market_config["secret_key"],
            "host": market_config["host"],
            "wss": market_config["wss"],
            "order_update_callback": self.on_event_order_update,
            "asset_update_callback": self.on_event_asset_update,
            "position_update_callback": self.on_event_position_update,
            "init_success_callback": self.on_event_init_success_callback,
        }
        self.trader = Trade(**cc)

        # 行情模块
        cc = {
            "platform": market_config["platform"],
            "symbols": [self.api_symbol],
            "channels": channels,
            "orderbook_length": 10,
            "orderbooks_length": 100,
            "klines_length": 100,
            "trades_length": 100,
            "wss": market_config["wss"],
            "orderbook_update_callback": self.on_event_orderbook_update,
            "kline_update_callback": self.on_event_kline_update,
            "trade_update_callback": self.on_event_trade_update
        }
        self.market = Market(**cc)

        self.ask1_price = 0  # 卖一价格
        self.bid1_price = 0  # 买一价格
        self.inited = True

    async def Buy(self, price, quantity):
        if self.trader.orders:
            trade_type = 1 if quantity > 0 else 2
            del_orders = []
            for order_id in self.market.trader.orders:
                if self.market.trader.orders[order_id].trade_type == trade_type:
                    del_orders.append(order_id)

            if del_orders:
                _, error = await self.market.trader.revoke_order(*del_orders)
                if error:
                    logger.error("[Cancel] cancel failed!", error)
                    return

        if quantity > 0:
            order_id, err = await self.trader.create_order('BUY', str(price), int(quantity), lever_rate=self.level)
        else:
            order_id, err = await self.trader.create_order('SELL', str(price), int(quantity), lever_rate=self.level)
        if err:
            logger.error("err: ", err)
            return
        return order_id

    async def Sell(self, price, quantity):
        if self.market.trader.orders:
            trade_type = 3 if quantity > 0 else 4
            del_orders = []
            for order_id in self.market.trader.orders:
                if self.market.trader.orders[order_id].trade_type == trade_type:
                    del_orders.append(order_id)

            if del_orders:
                _, error = await self.market.trader.revoke_order(*del_orders)
                if error:
                    logger.error("[Cancel] cancel failed!", error)
                    return

        if quantity > 0:
            order_id, err = await self.trader.create_order('SELL', str(price), quantity, lever_rate=self.level)
        else:
            order_id, err = await self.trader.create_order('BUY', str(price), quantity, lever_rate=self.level)
        if err:
            logger.error("err: ", err)
            return
        return order_id

    async def GetKLines(self, period, from_time, to_time=None):
        if to_time is None:
            to_time = time.time()
        ori_data, _ = await self._rest_api.get_klines(self.api_symbol, period, sfrom=int(from_time), to=int(to_time))
        if not ori_data:
            logger.info("Err, ", _)
            return
        data = ori_data['data']
        return data

    async def GetPosition(self):
        return self.trader.position

    def FetchFreeAsset(self):
        if not self.trader.assets or not self.trader.assets.assets.get(self.raw_symbol):
            return 0
        return float(self.trader.assets.assets.get(self.raw_symbol).get("free"))

    def FetchTotAsset(self):
        if not self.trader.assets or not self.trader.assets.assets.get(self.raw_symbol):
            return 0
        return float(self.trader.assets.assets.get(self.raw_symbol).get("total"))

    def CalResult(self):
        now_asset = self.FetchTotAsset()
        logger.info("Init asset: %r, end asset: %r" % (self.init_asset, now_asset))
        return True

    async def GetRecentKLine(self, period, size=200):
        ori_data, _ = await self._rest_api.get_klines(self.api_symbol, period, size=int(size))
        if not ori_data:
            return
        data = ori_data['data']
        return data

    def GetAskPrice(self):
        return self.ask1_price

    def GetBidPrice(self):
        return self.bid1_price

    async def on_event_orderbook_update(self, orderbook: Orderbook):
        """  orderbook更新
            self.market.orderbooks 是最新的orderbook组成的队列，记录的是历史N次orderbook的数据。
            本回调所传的orderbook是最新的单次orderbook。
        """
        if orderbook.asks:
            self.ask1_price = float(orderbook.asks[0][0])  # 卖一价格
        if orderbook.bids:
            self.bid1_price = float(orderbook.bids[0][0])  # 买一价格
        return

    async def on_event_order_update(self, order: Order):
        """ 订单状态更新
        """
        # logger.info("order: ", self.trader.orders)
        pass

    async def on_event_asset_update(self, asset: Asset):
        """ 资产更新
        """
        self.init_asset = self.FetchTotAsset()
        return

    async def on_event_position_update(self, position: Position):
        """ 仓位更新
        """
        # logger.info("position: ", self.trader.position)
        pass

    async def on_event_kline_update(self, kline: Kline):
        """ kline更新
            self.market.klines 是最新的kline组成的队列，记录的是历史N次kline的数据。
            本回调所传的kline是最新的单次kline。
        """
        return

    async def on_event_trade_update(self, trade: MarketTrade):
        """ market trade更新
            self.market.trades 是最新的逐笔成交组成的队列，记录的是历史N次trade的数据。
            本回调所传的trade是最新的单次trade。
        """
        return
    
    async def on_event_init_success_callback(self, success: bool, error: Error, **kwargs):
        """ init success callback
        """
        logger.debug("init success callback update:", success, error, kwargs, caller=self)

    def time(self):
        return time.time()

