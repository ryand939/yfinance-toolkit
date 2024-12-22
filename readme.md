# yFinance Data Analysis Toolkit

A Python toolkit that enhances [yfinance](https://github.com/ranaroussi/yfinance) to handle inconsistencies and missing pieces in Yahoo Finance's data. Provides reliable data access patterns and more information regarding dividends through data analysis.

## Why Use This Toolkit?

### Better Data Access & Reliability

- Handles transient API errors with smart retries
- Standardizes inconsistent field names
- Implements backup strategies and logic-based estimates to estimate or derive missing data
- Thread-safe SQLite caching system

### Dividend Analysis

- Calculates rates, yields, and payout ratios when Yahoo Finance doesn't provide such data
- Estimates future (and past) payment dates using pattern analysis
  - _Yahoo Finance only consistently provides historical **ex**-dividend dates, so past dividend dates must be estimated_
- Uses historical analysis and multiple strategies to estimate dates based on the given data

### Example Use Cases:

- Finding actual dividend payment dates (not just ex-dividend dates)
- Predicting future payment schedules to estimate future dividend income
- Getting reliable dividend data when Yahoo Finance's fields are inconsistent
- Analyzing multiple stocks at once

## Installation & Dependencies

```bash
# clone the repository
git clone https://github.com/ryand939/yfinance-toolkit
cd yfinance-toolkit

# create and activate a virtual environment
python -m venv venv
source venv/bin/activate # for linux or macOS
# or
venv\Scripts\activate # for windows

# Install dependencies
pip install -r requirements.txt
```

The project requires the following dependencies:

```
yfinance==0.2.50        # source of all Yahoo Finance data
pandas==2.2.3           # for data handling
numpy==2.2.0            # for numerical operations
backoff==2.2.1          # for retry mechanisms
```

## Project Structure

The code is organized into focused modules:

- `data/`: Handles yfinance API interaction
- `analysis/dividend/`: Contains dividend analysis logic
- `services/`: Services that provide additional functionality such as caching
- `utils/`: Helper functions for dates, retries, output, etc.
- `models/`: Data structures and type definitions

## Potential Extensions

While currently focused on dividend analysis, the toolkit could be expanded to analyze other areas:

- Financial statements
- Options data
- Earnings dates and forecasts
- Stock split history

## Usage Examples

### Basic Data Access

```python
from api.ticker_research import TickerResearch
from services.ticker_cache import StockCache
from datetime import timedelta

# Optional: Configure caching
cache = StockCache()
cache.set_duration(timedelta(hours=24))
cache.enable()

# Initialize research
ticker = TickerResearch("AAPL")

# Get standardized basic info
info = ticker.get_basic_info()
print(f"Price: ${info['price']}")
print(f"Sector: {info['sector']}")

# Access dividend data if available
if ticker.has_dividends():
    div_info = ticker.get_dividend_info()
    print(f"Annual Rate: ${div_info['dividend_rate']}")
    print(f"Yield: {div_info['dividend_yield']*100:.2f}%")
```

### Batch Processing

```python
from ticker_research import TickerBatchResearch

# Analyze multiple stocks
batch = TickerBatchResearch(["AAPL", "MSFT", "GOOGL"])

# Get prices for all tickers
prices = batch.get_all_prices()
for symbol, price in prices.items():
    print(f"{symbol}: ${price}")

# Filter for dividend-paying stocks only
div_stocks = batch.dividend_paying_only()

# Get an individual TickerResearch object for a symbol analyzed in batch
apple_data = batch.get_ticker("AAPL")
```

For more examples, check the `/examples` directory:

- `basic_usage.py`: Common operations and data retrieval examples
- `console_app.py`: Interactive command-line interface to get stock info
- `github_example.py`: Quick start example

See the [yfinance documentation](https://ranaroussi.github.io/yfinance/index.html) for all the available data

## Data Accuracy & Limitations

**Important Note About Estimates:**

- Payment date estimates are typically accurate within ±2-3 days when sufficient data is available, but in some cases very little data is provided
- The `estimation_method` field in results indicates how the data was estimated:

  - Methods for estimating the usual gap between ex-dividend and dividend dates rely on the stock calendar:

    - `exdiv_predicted_direct_calendar`: Detected outdated ex-dividend. Predict the real ex-dividend date and take the gap.
    - `div_predicted_direct_calendar`: Detected outdated dividend. Adjust dates to the same cycle and take the gap.
    - `direct_from_calendar`: Most accurate, some stocks show the correct future ex-dividend and dividend payout dates, then I can easily understand their dividend date patterns
    - `default_fallback_guess`: There is no calendar for the stock, so there is no data recorded of when a dividend has ever been paid out. The gap is then assigned a default fallback value based on minimal logic

  - The last dividend date is estimated using the assumed gap and the ex-dividend dates:
    - `calendar_date_plus_one_interval`: The calendar data was determined to be stale, so the last dividend is likely one cycle after the stale data
    - `direct_from_calendar`: The calendar data was determined to be stale, but just stale enough that it is exactly the last dividend data. 100% accurate!
    - `ex_dividend_plus_gap_basic`: The last ex-dividend has the usual gap added onto it, and that is the last dividend date
    - `previous_ex_dividend_plus_gap`: The last ex-dividend has the usual gap added onto it, but the new date is now in the future, retry with the second last ex-dividend date
    - `ex_dividend_plus_interval_projection`: The last ex-dividend has the usual gap added onto it, but it is one cycle too old. The average payout interval is added to get the last dividend date

- Accuracy depends entirely on data available from Yahoo Finance. Some stocks have very limited data (no calendar, inconsistent history), making accurate estimation impossible

## Credit

This project builds upon [yfinance](https://github.com/ranaroussi/yfinance) by Ran Aroussi. See the [yfinance documentation](https://ranaroussi.github.io/yfinance/index.html) for API details.
