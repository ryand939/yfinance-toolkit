# src/console_app.py

import time
import signal
from typing import List, Any

from src.services.ticker_cache import StockCache
from src.ticker_research import TickerResearch, TickerBatchResearch


class StockAnalyzerConsole:
    
    def __init__(self):
        # init console app with cache and settings
        self.cache = StockCache()
        self.commands = {
            'help': self.show_help,
            'exit': self.exit_console,
            'cache': self.handle_cache_command,
            'clear': lambda: print('\n' * 100)
        }

        # ctrl+c handler
        signal.signal(signal.SIGINT, self.handle_interrupt)

    def show_help(self) -> None:
        # show available commands and cache details as system status
        start_time = time.time()
        cache_status = "enabled" if self.cache.cache_enabled else "disabled"
        help_text = f"""
System Status:
-------------
Cache: {cache_status}
Cache Duration: {self.cache.cache_duration}
Cache Location: {self.cache.db_path}

Available Commands:
------------------
symbol1 symbol2 ...  : Analyze stocks (e.g., 'AAPL MSFT BCE.TO' or 'MFC.TO')
cache toggle         : Toggle cache usage on/off
cache clear          : Clear all cached data
help                 : Show this help message
clear                : Clear the screen
exit | Ctrl+C        : Exit the program

Note: Stock symbols can be entered directly, separated by spaces."""
        print(help_text)
        self._print_execution_time(start_time)


    # cache related commands 
    def handle_cache_command(self, subcommand: str = '') -> None:
        start_time = time.time()
        if subcommand == 'toggle':
            if self.cache.cache_enabled:
                self.cache.disable()
                print("Cache disabled")
            else:
                self.cache.enable()
                print("Cache enabled")
        elif subcommand == 'clear':
            if self.cache.clear():
                print("Cache cleared successfully")
            else:
                print("Error clearing cache")
        else:
            print("Invalid cache command. Use 'cache toggle' or 'cache clear'")
            
        self._print_execution_time(start_time)


    # analyze stock symbols and display results
    def analyze_symbols(self, symbols: List[str]) -> None:
        start_time = time.time()
        
        try:
            # just always do batch
            batch = TickerBatchResearch(symbols)
            for symbol, ticker in batch.tickers.items():
                self._print_stock_results(symbol, ticker)
                print()
        except Exception as e:
            print(f"Error analyzing stocks: {str(e)}")
            
        self._print_execution_time(start_time)



    # format and print TickerResearch obj
    def _print_stock_results(self, symbol: str, ticker: TickerResearch) -> None:
        width = 62
        padding = " " * 4
        
        def print_centered(text: str):
            print(f"{padding}{text:^{width}}")
            
        def print_header(text: str):
            print(f"\n{padding}{'─' * width}")
            print_centered(text)
            print(f"{padding}{'─' * width}")
            
        def print_field(label: str, value: Any, prefix: str = ""):
            if value is not None:
                print(f"{padding}{prefix}{label:<35} {value}")

        # check what data is available
        status = ticker.get_status()
        
        # header
        print("\n" + "═" * (width + 8))
        basic_info = ticker.get_basic_info()
        print_centered(f"{symbol.upper()} ANALYSIS")
        if basic_info.get('name'):
            print_centered(basic_info['name'])
        print("═" * (width + 8))


        # skip stock that doesnt pay div - this is supposed to be a div analysis program!
        if not status['has_dividends']:
            print_centered("This stock does not pay dividends")
            return

        # basic info
        print_header("BASIC INFORMATION")
        if basic_info.get('price'):
            print_field("Current Price", f"${basic_info['price']:,.2f}")
        print_field("Exchange", basic_info.get('exchange'))
        print_field("Sector", basic_info.get('sector'))
        print_field("Industry", basic_info.get('industry'))

        # dividend info
        if status['is_dividend_stock']:
            print_header("DIVIDEND INFORMATION")
            div_info = ticker.get_dividend_info()
            
            if div_info.get('dividend_rate'):
                print_field("Annual Dividend Rate", f"${div_info['dividend_rate']:,.4f}")
            if div_info.get('dividend_yield'):
                print_field("Dividend Yield", f"{div_info['dividend_yield']*100:.2f}%")
            if div_info.get('payout_ratio'):
                print_field("Payout Ratio", f"{div_info['payout_ratio']*100:.2f}%")
                print_field("  • Calculation Method", f"{div_info['calculation_methods']["payout_ratio_method"]}")
            if div_info.get('frequency'):
                print_field("Payment Frequency", div_info['frequency'].title())
            if div_info.get('average_interval_days'):
                print_field("Average Interval", f"{div_info['average_interval_days']} days")

            # gap analysis
            gap_analysis = ticker.get_gap_analysis()
            if gap_analysis:
                print_field("Gap Between Ex-Div and Payment", f"{gap_analysis['gap_days']} days")
                print_field("  • Confidence", gap_analysis['confidence'])
                print_field("  • Estimation Method", gap_analysis['estimation_method'])

            # last div payout details
            last_div = ticker.get_last_dividend()
            if last_div.get('date') and last_div.get('amount'):
                print_header("LAST DIVIDEND")
                print_field("Amount", f"${last_div['amount']:,.4f}")
                print_field("Date", last_div['date'])
                print_field("Estimation Method", last_div['estimation_method'])

            # estimated future div payout
            future_dates = ticker.get_future_dates()
            if future_dates:
                print_header("ESTIMATED FUTURE PAYMENTS")
                for i, date in enumerate(future_dates[:4], 1):
                    print_field(f"Payment {i}", date)

            # historical ex-dividend data pattern analysis
            pattern = ticker.get_ex_dividend_pattern()
            if pattern:
                print_header("EX-DIVIDEND DATE PATTERN ANALYSIS")
                print_field("Average Day of Month", f"{pattern['mean_day_of_month']:.1f}")
                print_field("Standard Deviation", f"{pattern['std_dev_days']:.1f} days")
                print_field("Day Range", f"{pattern['day_range']['min']} to {pattern['day_range']['max']}")



    # print execution time of command for the sake of showing how useful caching is
    def _print_execution_time(self, start_time: float) -> None:
        execution_time = time.time() - start_time
        print(f"\nExecution time: {execution_time:.2f} seconds")


    # handle keyboard interrupt ctrl+c
    def handle_interrupt(self, signum, frame):
        print("\nCtrl+C detected, exiting...")
        self.exit_console()


    # handle exit command
    def exit_console(self) -> None:
        print("\nThank you for using Stock Analyzer Console!")
        exit(0)


    # main console app loop
    def run(self) -> None:
        print("""
╔════════════════════════════════════════════════════╗
║             Stock Analyzer Console                 ║
║                                                    ║
║    Type 'help' for available commands              ║
║    Enter stock symbols directly (e.g. AAPL MSFT)   ║
╚════════════════════════════════════════════════════╝
""")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                
                # take input as list 
                parts = user_input.split()

                # first part might be command
                command = parts[0].lower()

                # parts after first might be command arguments
                args = parts[1:]
                
                # check if first part is command, route it accordingly
                if command in self.commands:
                    if command == 'cache' and args:
                        self.handle_cache_command(args[0])
                    else:
                        self.commands[command]()
                else:
                    # not a command, treat input as list of symbols and analyze them
                    self.analyze_symbols(user_input.split())
                    
            except Exception as e:
                print(f"Error: {str(e)}")


def main():
    console = StockAnalyzerConsole()
    console.run()


if __name__ == "__main__":
    main()