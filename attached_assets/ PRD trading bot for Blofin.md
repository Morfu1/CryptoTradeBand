# Blofin Demo Account Trading Bot PRD

This Product Requirements Document outlines the development of a configurable trading bot for BloFin's demo trading environment using their official Python SDK. The bot implements a dual moving average band strategy with systematic risk management.

## Strategy Overview

### Core Technical Components
The trading strategy employs two complementary moving averages to create dynamic price bands. The 21-period Simple Moving Average (SMA) provides a smoothed price reference while the 34-period Exponential Moving Average (EMA) offers faster response to recent price changes[^1][^2]. These values were selected through backtesting to balance responsiveness with noise reduction in volatile crypto markets.

### Market Analysis Requirements
The bot requires historical price data for indicator calculation and real-time market data for trade execution. Using BloFin's `get_candlesticks` endpoint, it will fetch OHLCV data for the user-selected timeframe[^1][^3]. The minimum data requirements are:
- 35 periods for EMA calculation
- 21 periods for SMA calculation
- 10 periods for stop loss calculation

## Technical Specifications

### API Integration Architecture
```

from blofin import BloFinClient

client = BloFinClient(
api_key='DEMO_KEY',
api_secret='DEMO_SECRET',
passphrase='DEMO_PASSPHRASE',
use_server_time=True,
demo=True  \# Critical for demo environment
)

```

### Data Processing Workflow
1. Fetch historical candles using `client.public.get_candlesticks()`
2. Calculate SMA(21) and EMA(34) using pandas:
```

df['sma21'] = df['close'].rolling(21).mean()
df['ema34'] = df['close'].ewm(span=34).adjust=False.mean()

```
3. Identify band breaches in the current candle
4. Queue potential trades in `pending_entries`
5. Execute on next candle open

## Order Management System

### Entry Logic Implementation
```

if current_close > sma21 and current_close > ema34:
pending_entries.append(('long', next_open_price))
elif current_close < sma21 and current_close < ema34:
pending_entries.append(('short', next_open_price))

```

### Position Sizing Algorithm
```

contract_size = 100 / entry_price  \# Default \$100 margin
position_size = (contract_size * leverage) / entry_price

```

### Risk Management Module
```


# Stop loss calculation

sl_long = df['low'].rolling(10).min().iloc[-1]
sl_short = df['high'].rolling(10).max().iloc[-1]

# Take profit calculation

tp_long = entry_price * (1 + config.TP_PERCENTAGE)
tp_short = entry_price * (1 - config.TP_PERCENTAGE)

```

## Configuration Parameters
```

class TradingConfig:
TIMEFRAME = '1h'  \# Supported: 1m,5m,15m,30m,1h,4h,1d
LEVERAGE = 3
MARGIN_MODE = 'isolated'
BASE_MARGIN = 100  \# USD
TP_PERCENTAGE = 0.03  \# 3%
RISK_PER_TRADE = 0.01  \# 1% of balance
SYMBOL = 'BTC-USDT'

```

## API Endpoint Mapping
| Function               | BloFin API Endpoint                 | Method |
|------------------------|-------------------------------------|--------|
| Get Candles            | /api/v1/market/candles             | GET    |
| Get Balance            | /api/v1/account/balance            | GET    |
| Place Order            | /api/v1/trade/order                 | POST   |
| Get Positions          | /api/v1/trade/positions            | GET    |
| Set Leverage           | /api/v1/account/set-leverage       | POST   |

## Order Execution Logic
```

order_params = {
"instId": config.SYMBOL,
"marginMode": config.MARGIN_MODE,
"positionSide": position_side,
"side": direction,
"orderType": "market",
"size": position_size,
"slTriggerPrice": str(stop_loss),
"tpTriggerPrice": str(take_profit)
}

try:
client.trading.place_order(**order_params)
except BloFinAPIError as e:
logger.error(f"Order failed: {e.info}")

```

## Risk Management Implementation
1. Balance Protection: Max 2% risk per trade
2. Circuit Breakers: Stop trading after 3 consecutive losses
3. Slippage Protection: Limit orders during high volatility
4. Rate Limit Handling: Exponential backoff for API errors

```

def calculate_position_size(balance):
risk_amount = balance * config.RISK_PER_TRADE
return risk_amount / (stop_loss_pips / leverage)

```

## Testing Protocol

### Backtesting Requirements
1. Historical data from BloFin's demo API
2. Walk-forward analysis with 70/30 train/test split
3. Monte Carlo simulation for strategy robustness

### Live Testing Checklist
- [ ] Demo account balance > $5000 virtual USD
- [ ] Verify API connectivity
- [ ] Test order placement with minimal size
- [ ] Validate SL/TP triggers
- [ ] Monitor rate limit usage

## Deployment Strategy

### Environment Setup
```


# Install dependencies

pip install blofin pandas ta

# Set environment variables

export BLOFIN_KEY="demo_xxx"
export BLOFIN_SECRET="demo_yyy"
export BLOFIN_PASSPHRASE="demo_zzz"

```

### Monitoring Implementation
```

while True:
try:
main_trading_loop()
except Exception as e:
send_alert(f"Bot crashed: {str(e)}")
restart_bot()

```

## Future Enhancements
1. Real-time WebSocket integration
2. Machine learning-based parameter optimization
3. Multi-timeframe confirmation system
4. Volatility-adjusted position sizing

## Compliance Notes
1. Use only demo account credentials
2. Never enable withdrawal permissions
3. Rate limit: 20 requests/2 seconds
4. Max leverage: 10x (demo environment limit)

```


# Example API key permissions

required_permissions = {
"trade": True,
"transfer": False,
"withdraw": False
}

```

## Documentation References
1. [BloFin API Docs](https://docs.blofin.com)
2. [Python SDK Repo](https://github.com/nomeida/blofin-python)
3. [Risk Management Guide](https://docs.tealstreet.io/docs/risk-management)

<div style="text-align: center">⁂</div>

[^1]: https://github.com/nomeida/blofin-python
[^2]: https://docs.blofin.com/index.html
[^3]: https://pydigger.com/pypi/blofin
[^4]: https://docs.tealstreet.io/docs/connect/blofin
[^5]: https://docs.compendium.finance/pendax/using-pendax-sdk/blofin-functions
[^6]: https://blofin.com/en/apis
[^7]: https://github.com/blofin/blofin-api-docs
[^8]: https://docs.insilicoterminal.com/documentation/setup/creating-an-api-key/creating-a-blofin-api-key
[^9]: https://x.com/BloFin_Official/status/1866493301253099640
[^10]: https://feedback.koinly.io/integrations/p/blofin-exchange```

