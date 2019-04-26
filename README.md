# Тестовое задание

(читать Market Clients for new developers.odt)

#### Необходимо разобраться в исходных базовых классах и, используя их, сделать следующее:  

Написать класс клиента (вместе с конвертером) для REST API биржи Okex, который реализует 2 функции:  
* Получение трейдов (trades) (метод fetch_trades_history)  
* Получение свечей (kline/candlestick) (метод fetch_candles)  

Написать класс клиента (вместе с конвертером) для Websocket API биржи Okex, который реализует 2 функции:  
* Получение трейдов (trades)  
* Получение свечей (kline/candlestick)

### hqlib
Common library for HyperQuant projects on Python

### Install

As separate project:

    pipenv install

Add as a library to your project:

    pipenv install -e git+https://github.com/hyperquant-platform/hqlib.git#egg=hqlib

Then, to update after hqlib changed:

    pipenv update
