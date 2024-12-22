from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import pandas as pd
from datetime import date
from analysis.dividend.dividend_calculations import DividendCalculator
from data.yfinance_adapter import yFinanceAdapter
from analysis.dividend.dividend_analysis import DividendPatternAnalyzer
from models.dividend_models import ExDividendPattern, DividendGapResult
from utils.date_util import DateNormalizer
from utils.get_redundant_field import get_redundant_field
from services.ticker_cache import use_cache

@dataclass
class TickerResearch:
    """
    Main interface for accessing and analyzing stock dividend data.
    
    Handles data fetching, caching, and comprehensive dividend analysis.
    All ticker operations go through this class to maintain consistent access patterns.
    """
    symbol: str
    
    
    @use_cache
    def __post_init__(self):
        """
        Initialize components and perform analysis on ticker.
        
        Sets up market data connection, analyzer, and cache handling.
        Caching behavior controlled by @use_cache decorator.
        """
        
        self._market_data = yFinanceAdapter()
        self._analyzer = DividendPatternAnalyzer()
        
        # fetch raw data
        self._fetch_data()
        
        # core dividend analysis
        self._analyze_patterns()



    
    def _fetch_data(self) -> None:
        """
        Fetch all raw data from Yahoo Finance.
        
        Retrieves stock info, calendar data, and ex-dividend history.
        Stores error info if an operation fails.

        There exists more data beyond info/calendar/dividends, but it is not relevant to this project
        """
        try:
            self.info: Dict[str, Any] = self._market_data.get_stock_info(self.symbol)
            self.calendar: Dict[str, Any] = self._market_data.get_calendar_data(self.symbol)
            self.dividends: pd.Series = self._market_data.get_dividend_history(self.symbol)
            self.error = None
        except Exception as e:
            self.info = {}
            self.calendar = {}
            self.dividends = pd.Series(dtype=float)
            self.error = str(e)



    
    def _analyze_patterns(self) -> None:
        """
        Perform initial analysis of dividend patterns.
        
        Calculates/estimates frequency, gaps, and statistical patterns.
        Sets defaults for all metrics if analysis fails.
        """
        try:
            # dividend analysis
            self._frequency, self._avg_interval = self._analyzer.analyze_dividend_frequency(self.dividends)
            
            # case no dividends
            if self._avg_interval is None:
                self._gap_result = DividendGapResult(0, False, "no_dividend_history")
                self._pattern = ExDividendPattern(0, 0, 0, 0)
                self._staleness = 1.1
                return
                
            # analysis for dividend paying stocks
            self._gap_result = self._analyzer.analyze_dividend_gap(self.calendar, self._avg_interval)
            self._pattern = self._analyzer.analyze_ex_dividend_patterns(self.dividends)
            
            self._staleness = (
            self._analyzer.calculate_staleness_threshold(
                self._avg_interval,
                self._pattern
            ) if self._avg_interval else 1.1
        )
        except Exception as e:
            print(f"Analysis failed for {self.symbol}: {str(e)}")
            self._frequency = None
            self._avg_interval = None
            self._gap_result = DividendGapResult(0, False, "analysis_failed")
            self._pattern = ExDividendPattern(0, 0, 0, 0)
            self._staleness = 1.1



    
    def get_info(self) -> Dict[str, Any]:
        """
        Get complete stock info dictionary.
        
        Returns:
            Dict[str, Any]: Raw info dictionary from Yahoo Finance
        """
        return self.info



    
    def get_calendar(self) -> Dict[str, Any]:
        """
        Get complete stock calendar dictionary.
        
        Returns:
            Dict[str, Any]: Raw calendar dictionary from Yahoo Finance
        """
        return self.calendar



    
    def get_dividends(self) -> pd.Series:
        """
        Get complete stock (ex-)dividend history.
        
        Returns:
            pd.Series: Raw (ex-)dividend series from Yahoo Finance
        """
        return self.dividends



    
    def get_raw_data(self) -> Dict[str, Any]:
        """
        Get all raw data components.
        
        Returns:
            Dict containing:
            - info: Raw Yahoo Finance info dictionary
            - calendar: Calendar dates dictionary
            - dividends: Historical (ex-)dividend Series
            - error: Error message if fetch failed, None otherwise
        """
        return {
            "info": self.info,
            "calendar": self.calendar,
            "dividends": self.dividends,
            "error": self.error
        }



    
    def get_gap_analysis(self) -> Dict[str, Any]:
        """
        Get analysis of gap between ex-dividend and payment dates.
        
        Returns:
            Dict containing:
            - gap_days: Expected number of days between ex-dividend and dividend dates
            - confidence: Confidence level in estimation
            - estimation_method: Method used to estimate the usual gap
        """
        return{
            "gap_days": self._gap_result.gap_days,
            "confidence": self._gap_result.confidence,
            "estimation_method": self._gap_result.estimation_method
        }



    
    def get_pattern_analysis(self) -> ExDividendPattern:
        """
        Get ex-dividend pattern analysis result.
        
        Returns:
            ExDividendPattern containing statistical metrics:
                - mean_day_of_month: Average day ex-div occurs
                - std_dev_days: Standard deviation in days
                - min_day: Earliest observed day
                - max_day: Latest observed day
        """
        return self._pattern



    
    def has_dividends(self) -> bool:
        """
        Check if stock has dividend history.
        
        Returns:
            bool: True if stock has any dividend history,
                False if dividend history is empty
        """
        return not self.dividends.empty



    
    def has_calendar(self) -> bool:
        """
        Check if stock has calendar data.
        
        Returns:
            bool: True if calendar dictionary contains data,
                False if calendar is empty
        """
        return bool(self.calendar)



    
    def get_analysis_metrics(self) -> Dict[str, Any]:
        """
        Get all analysis metrics.
        
        Returns:
            Dict containing:
            - frequency: Payment frequency (monthly/quarterly/etc)
            - average_interval: Average days between dividend payouts
            - gap_result: Expected gap between ex-dividend and dividend payout
            - pattern: Historical ex-dividend date pattern metrics
            - staleness_threshold: Data freshness threshold
        """
        return {
            "frequency": self._frequency,
            "average_interval": self._avg_interval,
            "gap_result": self._gap_result.__dict__,
            "pattern": self._pattern.__dict__,
            "staleness_threshold": self._staleness
        }



    
    def get_calendar_dates(self) -> Dict[str, Optional[date]]:
        """
        Get the calendar dates relevant to this program with validation.
        There is more information available in self.calendar if it exists, but that info is not relevant to my program.
        
        Returns:
            Dict containing:
            - dividend_date: Next dividend payment date if available
            - ex_dividend_date: Next ex-dividend date if available
            Both None if calendar data unavailable
        """
        if not self.calendar:
            return {
                "dividend_date": None,
                "ex_dividend_date": None
            }
        return {
            "dividend_date": DateNormalizer.normalize_date(self.calendar["Dividend Date"])
                if "Dividend Date" in self.calendar else None,
            "ex_dividend_date": DateNormalizer.normalize_date(self.calendar["Ex-Dividend Date"])
                if "Ex-Dividend Date" in self.calendar else None
        }



    
    def get_status(self) -> Dict[str, bool]:
        """
        Get status of available stock data.
        
        Returns:
            Dict containing boolean flags:
            - has_dividends: True if (ex-)dividend history exists
            - has_calendar: True if calendar data exists
            - has_basic_info: True if basic info exists
            - has_error: True if error occurred
            - is_dividend_stock: True if stock pays dividends
        """
        return {
            "has_dividends": not self.dividends.empty,
            "has_calendar": bool(self.calendar),
            "has_basic_info": bool(self.info),
            "has_error": bool(self.error),
            "is_dividend_stock": self._frequency is not None
        }




    
    def get_price(self) -> Optional[float]:
        """
        Get current stock price.
        
        Returns:
            float: Current price of a stock or None if data is not available
        """
        return get_redundant_field(
            data=self.info, 
            primary_key="currentPrice", 
            backup_keys=["regularMarketPrice", "previousClose"]
            )
    


    
    def get_basic_info(self) -> Dict[str, Any]:
        """
        Get basic stock information.
        
        Returns:
            Dict containing standardized fields:
            - name
            - short_name
            - symbol
            - underlying_symbol
            - legal_type
            - sector
            - industry
            - currency
            - market_cap
            - fund_family
            - exchange
            - quote_type
            - price
            Values are "?" if they could not be found
        """
        fallback = "?"
        return {
            "name": self.info.get("longName", fallback),
            "short_name": self.info.get("shortName", fallback),
            "symbol": self.info.get("underlyingSymbol", fallback),
            "underlying_symbol": self.info.get("underlyingSymbol", fallback),
            "legal_type": self.info.get("legalType", fallback),
            "sector": self.info.get("sector", fallback),
            "industry": self.info.get("industry", fallback),
            "currency": self.info.get("currency", fallback),
            "market_cap": self.info.get("marketCap", fallback),
            "fund_family": self.info.get("fundFamily", fallback),
            "exchange": self.info.get("exchange", fallback),
            "quote_type": self.info.get("quoteType", fallback),
            "price": self.get_price()
        }



    
    def get_dividend_info(self) -> Dict[str, Any]:
        """
        Get comprehensive dividend information.
        
        Returns:
            Dict containing:
            - dividend_rate: Annual payout rate
            - dividend_yield: Current yield percentage
            - payout_ratio: Earnings payout ratio
            - frequency: Payment frequency (monthly/quarterly/etc)
            - average_interval_days: Average days between payments
            - calculation_methods
                - dividend_rate_method: Method used to calculate the dividend rate
                - payout_ratio_method: Method used to calculate the payout ratio
        """
        # base price for calculations
        price = self.get_price()
        
        # calculate dividend rate
        div_rate, rate_method = DividendCalculator.calculate_dividend_rate(
            price=price,
            info=self.info,
            dividends=self.dividends,
            frequency=self._frequency
        )
        
        # calculate payout ratio
        payout_ratio, ratio_method = DividendCalculator.calculate_payout_ratio(
            info=self.info,
            dividend_rate=div_rate
        )
        fallback = None
        return {
            "dividend_rate": div_rate if div_rate else fallback,
            "dividend_yield": get_redundant_field(self.info, "dividendYield", ["yield"]),
            "payout_ratio": payout_ratio if payout_ratio else fallback,
            "frequency": self._frequency,
            "average_interval_days": int(round(self._avg_interval)) if self._avg_interval else fallback,
            "ex_dividend_date": self._analyzer.get_latest_ex_date( self.info, self.calendar, self.dividends ),
            "calculation_methods": {
                "dividend_rate_method": rate_method,
                "payout_ratio_method": ratio_method
            }
        }



    
    def get_last_dividend(self) -> Dict[str, Optional[float | str]]:
        """
        Get the most recent dividend payment details.
        
        Returns:
            Dict containing:
            - date: ISO format payment date
            - amount: Payment amount
            - estimation_method: Method used to estimate last dividend date
        """
        return self._analyzer.get_last_dividend_info(
            self.dividends,
            self.calendar,
            self._gap_result.gap_days,
            self._avg_interval,
            self._pattern,
            self._staleness
        )



    
    def get_future_dates(self) -> Optional[List[str]]:
        """
        Predict future dividend dates.
            
        Returns:
            List of ISO format dates for predicted payments
            None if insufficient data for prediction
        """
        if self.dividends.empty:
            return None
        return self._analyzer.predict_future_dates(
            gap_days=self._gap_result.gap_days,
            avg_interval=self._avg_interval,
            last_ex_date=self.dividends.index[-1].date(),
            calendar=self.calendar,
            pattern=self._pattern,
            payout_timing=self._frequency or "quarterly"
        )



    
    def get_ex_dividend_pattern(self) -> Dict[str, float]:
        """
        Get detailed ex-dividend date pattern statistics.
        
        Note: This only tracks ex-dividend dates, not payment dates,
        due to Yahoo Finance data limitations.
        
        Returns:
            Dict containing:
            - mean_day_of_month: Average day ex-div occurs
            - std_dev_days: Standard deviation in days
            - day_range:
                - min: Earliest observed day
                - max: Latest observed day
        """
        return {
            "mean_day_of_month": self._pattern.mean_day_of_month,
            "std_dev_days": self._pattern.std_dev_days,
            "day_range": {
                "min": self._pattern.min_day,
                "max": self._pattern.max_day
            }
        }



    
    def get_ex_dividend_history(self) -> pd.Series:
        """
        Get historical ex-dividend data.
    
        Returns:
            pd.Series: Time series of historical ex-dividend dates and amounts,
                    Index contains dates, values contain amounts
        """
        return self.dividends
    



class TickerBatchResearch:
    """Handles batch processing of multiple tickers"""
    
    
    def __init__(self, symbols: List[str]):
        """
        Initialize TickerResearch objects for multiple tickers.
        
        Args:
            symbols: List of ticker symbols to retrieve
        """
        self.tickers: Dict[str, TickerResearch] = {
            symbol.upper(): TickerResearch(symbol)
            for symbol in symbols
        }



    
    def get_all_symbols(self) -> List[str]:
        """
        Get a list of all symbols in the batch.
        
        Returns:
            List[str]: All ticker symbols in uppercase
        """
        return list(self.tickers.keys())



    
    def get_ticker(self, symbol: str) -> Optional[TickerResearch]:
        """
        Get the TickerResearch object for a specific symbol.
        
        Args:
            symbol: Ticker symbol to retrieve
            
        Returns:
            Optional[TickerResearch]: TickerResearch object if found, None otherwise
        """
        return self.tickers.get(symbol.upper())



    
    def get_all_prices(self) -> Dict[str, Optional[float]]:
        """
        Get prices for all tickers.
        
        Returns:
            Dict mapping symbols to their current prices,
            None for any tickers where price is unavailable
        """
        return {
            symbol: ticker.get_price()
            for symbol, ticker in self.tickers.items()
        }



    
    def get_all_dividend_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get dividend info for all tickers.
        
        Returns:
            Dict mapping symbols to their dividend info dictionaries,
            Each containing rates, yields, and payment patterns
        """
        return {
            symbol: ticker.get_dividend_info()
            for symbol, ticker in self.tickers.items()
        }



    
    def get_future_dates_all(self) -> Dict[str, Optional[List[str]]]:
        """
        Get predicted dividend payout dates for all tickers.
        
        Returns:
            Dict mapping symbols to lists of predicted payment dates,
            None for tickers with insufficient data
        """
        return {
            symbol: ticker.get_future_dates()
            for symbol, ticker in self.tickers.items()
        }
    


    
    def get_all_status(self) -> Dict[str, Dict[str, bool]]:
        """
        Get information availability status for all tickers.
        
        Returns:
            Dict mapping symbols to status dictionaries,
            Each containing data availability flags
        """
        return {
            symbol: ticker.get_status()
            for symbol, ticker in self.tickers.items()
        }



    
    def get_all_gap_analysis(self) -> Dict[str, DividendGapResult]:
        """
        Get gap analysis for all tickers.
        
        Returns:
            Dict mapping symbols to their gap analysis results,
            Each containing gap days, confidence level, and estimation method
        """
        return {
            symbol: ticker.get_gap_analysis()
            for symbol, ticker in self.tickers.items()
        }



    
    def dividend_paying_only(self) -> Dict[str, TickerResearch]:
        """
        Get filtered dictionary of only stocks that pay a dividend.
        
        Returns:
            Dict[str, TickerResearch]: Dictionary mapping symbols to their
            TickerResearch objects, containing only stocks with dividend history
        """
        return {
            symbol: ticker 
            for symbol, ticker in self.tickers.items() 
            if ticker.has_dividends()
        }


    
    def __getitem__(self, symbol: str) -> Optional[TickerResearch]:
        """
        This allows you to access tickers like a dictionary.
        
        Args:
            symbol: Stock ticker symbol to retrieve
            
        Returns:
            Optional[TickerResearch]: TickerResearch object if found,
                                    None if symbol not in batch
        """
        return self.tickers.get(symbol.upper())