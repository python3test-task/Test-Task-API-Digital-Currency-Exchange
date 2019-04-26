from hyperquant.clients import utils

print('API методы trades и kline/candlestick для биржи okex.com')
rest_or_ws = int(input("Выберите Rest или WebSocket (для Rest введите 1, для WebSocket введите 2): "))
api_method = int(input("Выберите вызываемый метод: для trades - 1 для kline/candlestick - 2: "))


if rest_or_ws == 1:
    client = utils.create_rest_client(platform_id=4)
    if api_method == 1:
        print(client.fetch_trades_history(symbol='eth_btc'))
    elif api_method == 2:
        print(client.fetch_candles(symbol='eth_btc', interval='1min', limit=20))

elif rest_or_ws == 2:
    client = utils.create_ws_client(platform_id=4)
    if api_method == 1:
        client.trades(symbol='eth_btc')
    if api_method == 2:
        client.candles(symbol='eth_usdt', interval='1min')







