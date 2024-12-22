# src/basic_usage.py

from src.ticker_research import TickerResearch, TickerBatchResearch
from src.services.ticker_cache import StockCache
from src.utils.data_printer import print_data
from datetime import timedelta



def print_section(title: str):
    print(f"\n{'='*80}")
    print(f"{title.center(80)}")
    print('='*80 + '\n')



def format_currency(value: float) -> str:
    return f"${value:,.2f}" if value is not None else "N/A"



def format_percentage(value: float) -> str:
    return f"{value*100:.2f}%" if value is not None else "N/A"




def demonstrate_single_stock():
    
    print_section("Single Stock Analysis - ENB.TO")
    
    # setup cache
    cache = StockCache()
    cache.set_duration(timedelta(hours=12))
    cache.clear()
    cache.enable()
    
    # first fetch - will need fresh data
    title = "1. Initial Data Fetch:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    ticker = TickerResearch("ENB.TO")
    
    # check if ticker pays dividends
    status = ticker.get_status()
    if not status["has_dividends"]:
        print(f"\nNote: {ticker.symbol} does not pay dividends.")
        return
    
    # display basic info
    title = "2. Basic Stock Information:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    basic_info = ticker.get_basic_info()
    print_data(basic_info, "Basic Info")
    
    # display dividend analysis details
    title = "3. Dividend Analysis:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    div_info = ticker.get_dividend_info()
    print_data(div_info, "Dividend Info")
    
    # display the predicted last dividend
    last_div = ticker.get_last_dividend()
    print_data(last_div, "Last Dividend Details")
    
    # display the estimated future dividend dates
    title = "4. Future Dividend Projections:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    future_dates = ticker.get_future_dates()
    if future_dates:
        print("Estimated Future Dividend Dates:")
        for i, date in enumerate(future_dates, 1):
            print(f"  {i}. {date}")
    else:
        print("Unable to project future dividend dates.")
    
    # display the pattern analysis from historical ex-dividend dates
    title = "5. Historical Pattern Analysis:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    pattern = ticker.get_ex_dividend_pattern()
    print_data(pattern, "Ex-Dividend Date Patterns")
    
    # display the gap analysis information
    gap = ticker.get_gap_analysis()
    print_data(gap, "Payment Gap Analysis")
    
    # demonstrate cache usage
    title = "6. Cache Demonstration:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    print("Fetching same stock again (should use cache)...")
    ticker_cached = TickerResearch("ENB.TO")




def demonstrate_batch_analysis():
    
    print_section("Batch Stock Analysis")
    
    # set of stocks for demonstration
    symbols = ["AAPL", "AMZN", "MSFT", "ENB.TO"]
    print(f"Analyzing multiple stocks (one is still cached!): {', '.join(symbols)}")
    
    # init batch research, getting TickerResearch for each
    batch = TickerBatchResearch(symbols)
    
    # demonstrate different batch operations
    title = "1. Basic Info Comparison:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    for symbol, ticker in batch.tickers.items():
        basic = ticker.get_basic_info()
        print(f"\n{symbol}:")
        print(f"  Name: {basic.get('name', 'N/A')}")
        print(f"  Price: {format_currency(basic.get('price'))}")
        print(f"  Sector: {basic.get('sector', 'N/A')}")
    
    title = "2. Dividend Yield Comparison:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    for symbol, ticker in batch.tickers.items():
        status = ticker.get_status()
        if not status["has_dividends"]:
            print(f"{symbol}: No dividend")
            continue
            
        div_info = ticker.get_dividend_info()
        yield_val = div_info.get('dividend_yield')
        print(f"{symbol}: {format_percentage(yield_val)}")
    
    title = "3. Payment Frequency Comparison:"
    print(f"\n{title}")
    print("-" * (len(title) + 1))
    for symbol, ticker in batch.tickers.items():
        status = ticker.get_status()
        if not status["has_dividends"]:
            print(f"{symbol}: Non-dividend stock")
            continue
            
        div_info = ticker.get_dividend_info()
        freq = div_info.get('frequency', 'Unknown')
        interval = div_info.get('average_interval_days', 'N/A')
        
        freq_str = freq.title() if freq else "Unknown"
        print(f"{symbol}: {freq_str} (Avg interval: {interval} days)")




def main():

    print("\nDividend Analysis Tool Demonstration")
    print("\nThis demonstration will show both single-stock and batch analysis capabilities.")
    
    try:
        demonstrate_single_stock()
        print()
        demonstrate_batch_analysis()
        
    except Exception as e:
        print(f"\nError during demonstration: {str(e)}")
        raise
    
    print("\nDemonstration completed successfully!")

if __name__ == "__main__":
    main()