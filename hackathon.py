from blueshift.library.technicals.indicators import ema
from blueshift.api import symbol, order_percent, order, cancel_order, order_target_percent
from blueshift.api import set_stoploss, set_takeprofit, schedule_once
from blueshift.api import schedule_function, date_rules, time_rules, square_off
import talib as ta
import numpy as np
import pandas as pd

def initialize(context):
    context.params = {
            'lots':35,
            'stoploss':0.4,
            'takeprofit':0.7,
            'indicator_lookback': 25,
            'indicator_freq': '1m'
            }
    context.vix = symbol('INDIAVIX')
    context.nifty = symbol('NIFTY-I')
    context.stocks = ['RELIANCE', 'INFY', 'HDFCBANK', 'TCS', 'BANKNIFTY-I']
    context.securities = [symbol(s) for s in context.stocks]
    context.universe = [
        symbol('NIFTY-W0CE+0'),
        symbol('RELIANCE-IICE+0'),
        symbol('INFY-IICE+0'),
        symbol('HDFCBANK-IICE+0'),
        symbol('TCS-IICE+0')
        ]
    
    schedule_function(
            enter, date_rules.every_day(), 
            time_rules.market_open(5))
    schedule_function(
            close_out, date_rules.every_day(), 
            time_rules.market_close(30))
    
    context.traded = False

def before_trading_start(context, data):
    context.entered = set()
    context.traded = False 

def enter(context, data):

    if context.traded:
        return

    close_out(context, data)

    px_nifty = data.history(context.nifty, 'close',
        context.params['indicator_lookback'],
        context.params['indicator_freq'])
    ind9 = ema(px_nifty, 9)
    ind5 = ema(px_nifty, 5)
    size = context.params['lots']*context.nifty.mult
    price_vix = data.current(context.vix, 'close')

    if ind5 > ind9:
        order(symbol('NIFTY-W0CE-500'), size)
    else:
        order(symbol('NIFTY-W0PE-500'), size)
    
    for s in context.securities:
        if price_vix < 16:
            order(s, size)



    context.traded = True
    schedule_once(set_targets)
    

def close_out(context, data):
    square_off(context.securities)
    pass
    for oid in context.open_orders:
        cancel_order(oid)
        
    for asset in context.portfolio.positions:
        order(asset, 0)

def set_targets(context, data):
    # ALWAYS set stoploss and takeprofit targets on positions, 
    # not on order assets. See API documentation for more.
    for asset in context.portfolio.positions:
        if asset in context.entered:
            continue
        set_stoploss(asset, 'PERCENT', context.params['stoploss'])
        set_takeprofit(asset, 'PERCENT', context.params['takeprofit'])
        context.entered.add(asset)
        
    if len(context.universe) != len(context.entered):
        # one or more positions not traded yet, try again alter
        schedule_once(set_targets)