from src.ticker_research import TickerResearch
from src.utils.data_printer import print_data
from datetime import timedelta

# Optional: Use cache
from src.services.ticker_cache import StockCache

cache = StockCache()
cache.set_duration(timedelta(hours=24))
cache.clear()
cache.enable()


# Analyze a single stock
ticker = TickerResearch("AAPL")

# Get basic information
basic_info = ticker.get_basic_info()
print(f"Company: {basic_info['name']}")
print(f"Current Price: ${basic_info['price']}")

# Get dividend information
if ticker.has_dividends():
    div_info = ticker.get_dividend_info()
    print(f"Dividend Rate: ${div_info['dividend_rate']}")
    print(f"Dividend Yield: {div_info['dividend_yield']*100:.2f}%")
    print(f"Payment Frequency: {div_info['frequency']}")

    # Last Dividend Payout Info
    last_div = ticker.get_last_dividend()
    print_data(last_div, "Last Dividend Details")

print("\nAAPL should now be cached if I try to fetch data again:")
ticker = TickerResearch("AAPL")