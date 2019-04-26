import zlib
import json
#import websocket
from websocket import WebSocketApp
from threading import Thread
#import logging

from hyperquant.api import Platform, Interval, Sorting, Direction
from hyperquant.clients import RESTConverter, PrivatePlatformRESTClient, WSConverter, WSClient, \
    ParamName, Endpoint, Trade, Candle, Error


# REST
class OkexRESTConverterV1(RESTConverter):
    base_url = "https://www.okex.com/api/v{version}"

    # Settings:

    # Converting info:
    # For converting to platform
    endpoint_lookup = {
        Endpoint.TRADE_HISTORY: "trades.do",
        Endpoint.CANDLE: "kline.do",
    }
    param_name_lookup = {
        ParamName.SYMBOL: "symbol",
        ParamName.LIMIT: "size",
        ParamName.IS_USE_MAX_LIMIT: None,
        ParamName.INTERVAL: "type",
    }

    # For parsing
    param_lookup_by_class = {
        Error: {
            "error_code": "code",
        },
        Trade: {
            "tid": ParamName.ITEM_ID,
            #"date": ParamName.TIMESTAMP,
            "date_ms": ParamName.TIMESTAMP,
            "price": ParamName.PRICE,
            "amount": ParamName.AMOUNT,
            "type": ParamName.DIRECTION,            
        },
        Candle: [
            ParamName.TIMESTAMP,
            ParamName.PRICE_OPEN,
            ParamName.PRICE_HIGH,
            ParamName.PRICE_LOW,
            ParamName.PRICE_CLOSE,
            ParamName.AMOUNT,
        ],        
    }

    # For converting time
    is_source_in_milliseconds = True


class OkexRESTClient(PrivatePlatformRESTClient):
    platform_id = Platform.OKEX
    version = "1"  # Default version

    _converter_class_by_version = {
        "1": OkexRESTConverterV1,
    }
    
    def fetch_trades_history(self, symbol, limit=None, from_item=None, sorting=None, from_time=None, to_time=None, **kwargs):
        return super().fetch_trades_history(symbol, limit, from_item, sorting=sorting, from_time=from_time, to_time=to_time, **kwargs)

    def fetch_candles(self, symbol, interval, limit=None, from_time=None, to_time=None, is_use_max_limit=False, version=None, **kwargs):
        return super().fetch_candles(symbol, interval, limit, from_time, to_time, is_use_max_limit, version=version, **kwargs)


# WebSocket

class OkexWSConverterV1(WSConverter):
    # Main params:
    base_url = "wss://real.okex.com:10440/ws/v{version}"
    
    supported_endpoints = [Endpoint.TRADE, Endpoint.CANDLE]
    symbol_endpoints = [Endpoint.TRADE, Endpoint.CANDLE]

    endpoint_lookup = { 
        Endpoint.TRADE: 'ok_sub_spot_{symbol}_deals',
        Endpoint.CANDLE: 'ok_sub_spot_{symbol}_kline_{interval}',
    }

    #ParamName.INTERVAL: {
    #    Interval.MIN_1: '1min',
    #}

    param_name_lookup = {
        ParamName.SYMBOL: "symbol",
        ParamName.INTERVAL: "interval",
    }

    # By properties:
    ParamName.DIRECTION: {          # Sell/buy or ask/bid
        Direction.SELL: "ask",
        Direction.BUY: "bid",
    }
    
    # For parsing
    param_lookup_by_class = {
        # Error
        Error: {
            'error_msg': 'message',
            'error_code': 'code',
        },
        # Data
        # tid, price, amount, time, type
        Trade: [
            ParamName.TRADE_ID,
            ParamName.PRICE,
            ParamName.AMOUNT,
            ParamName.TIMESTAMP,
            ParamName.DIRECTION
        ],
        Candle: [
            ParamName.TIMESTAMP,
            ParamName.PRICE_OPEN,
            ParamName.PRICE_HIGH,
            ParamName.PRICE_LOW,
            ParamName.PRICE_CLOSE,
            ParamName.AMOUNT
        ],
    }

    def _generate_subscription(self, endpoint, symbol=None, **params):
        return super()._generate_subscription(endpoint, symbol.lower() if symbol else symbol, **params)

    def parse(self, endpoint, data):
        if "data" in data:
            data = data["data"]
        return super().parse(endpoint, data)

    def _parse_item(self, endpoint, item_data):
        if endpoint == Endpoint.CANDLE and "data" in item_data:
            item_data = item_data["data"]
        return super()._parse_item(endpoint, item_data)


class OkexWSClient(WSClient):
    platform_id = Platform.OKEX
    version = "1"  # Default version

    _converter_class_by_version = {
        "1": OkexWSConverterV1,
    }    
    
    params_for_subscribe = {}  # сохраняем **params из subscribe()
    
    def inflate(self, data):
        decompress = zlib.decompressobj(-zlib.MAX_WBITS)
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated
    
    def _send_subscribe(self, subscriptions):
        for line in subscriptions:
            event_data = {"event": "addChannel", "channel": line}
        self._send(event_data)


    def _on_message(self, message):
        self.logger.debug("On message: %s", message[:200])
        # str -> json
        message = self.inflate(message)        
        try:
            data = json.loads(message)          
        except json.JSONDecodeError:  
            self.logger.error("Wrong JSON is received! Skipped. message: %s", message)
            return
        # json -> items
        result = self._parse(None, data)
        # Process items
        self._data_buffer = []
        print("   result: \n", result)      ############## печатаем в консоль результат
        if result and isinstance(result, list):
            for item in result:
                self.on_item_received(item)
        else:
            self.on_item_received(result)

        if self.on_data and self._data_buffer:
            self.on_data(self._data_buffer)       

         
    # Connection
    def connect(self, version=None):
        # Check ready
        if not self.current_subscriptions:
            self.logger.warning("Please subscribe before connect.")
            return
        # Do nothing if was called before
        if self.ws and self.is_started:
            self.logger.warning("WebSocket is already started.")
            return
        # Connect
        #websocket.enableTrace(True)
        if not self.ws:
            self.ws = WebSocketApp(self.url,
                                   header=self.headers,
                                   on_open=self._on_open,
                                   on_message=self._on_message,
                                   on_error=self._on_error,
                                   on_close=self._on_close)
        else:
            self.ws.url = self.url
            self.ws.header = self.headers
        
        # (run_forever() will raise an exception if previous socket is still not closed)
        self.logger.debug("Start WebSocket with url: %s" % self.ws.url)
        self.is_started = True
        self.thread = Thread(target=self.ws.run_forever)
        #self.thread.daemon = True
        self.thread.start()
        #self.ws.run_forever()


    def subscribe(self, endpoints=None, symbols=None, **params):
        if params:
            self.params_for_subscribe = params
        else:
            params = self.params_for_subscribe
        super().subscribe(endpoints, symbols, **params)


#######################

    def trades(self, symbol):
        self.subscribe(endpoints=[Endpoint.TRADE], symbols=[symbol])       

    def candles(self, symbol, interval):
        self.subscribe(endpoints=[Endpoint.CANDLE], symbols=[symbol], interval=interval)

