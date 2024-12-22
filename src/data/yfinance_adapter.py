# src\data\yfinance_adapter.py

from typing import Dict, Any, Optional
import yfinance as yf
from requests import Session
import pandas as pd
from src.utils.retry_util import smart_retry
from src.utils.ignore_warnings import silence_yfinance_warnings
from src.utils.exceptions import yFinanceError

class yFinanceAdapter():
    """

    Adapter for fetching stock data from Yahoo Finance API.
    
    Handles data fetching, error handling, and retries when Yahoo Finance API is being temperamental. 
    The API sometimes returns 404s for valid tickers or claims they don't exist - these cases are handled via retries.

    Also, when a stock doesnt have a calendar, a 404 error is printed in console, I silence this with the 
    @silence_yfinance_warnings decorator on the get_calendar_data function. This is completely optional and can be removed.

    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize adapter with optional custom session.
        
        Args:
            session: Optional requests Session for customized request handling
        """
        self.session = session




    @smart_retry(
        max_tries=3,
        allowed_exceptions=(yFinanceError,)
    )
    def _fetch_ticker(self, symbol: str) -> yf.Ticker:
        """
        Create yFinance ticker instance with retry handling.
        
        Occasionally Yahoo Finance claims valid symbols don't exist.
        The retry decorator handles these transient errors.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            yf.Ticker: Initialized ticker object
            
        Raises:
            yFinanceError: When ticker cannot be fetched after retries
        """
        return yf.Ticker(symbol, session=self.session)




    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete stock information dictionary.
        
        Contains a ton of random data about the stock including:
        - Current price and trading info
        - Company details and financials  
        - Some dividend and earnings data
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dict containing stock information or empty dict if fetch fails
        """
        ticker = self._fetch_ticker(symbol)
        return ticker.info or {}




    def get_dividend_history(self, symbol: str) -> pd.Series:
        """
        Get historical ex-dividend data.
        
        Note: yFinance only provides ex-dividend dates for some reason, not payment dates.
        Returns empty series for non-dividend stocks.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Series containing ex-dividend history, sorted by date
        """
        ticker = self._fetch_ticker(symbol)
        dividends = ticker.dividends
        return dividends.sort_index() if dividends is not None else pd.Series(dtype=float)




    @silence_yfinance_warnings
    def get_calendar_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get upcoming dividend calendar data if available.
        
        Many stocks don't have calendar data, causing 404 errors.
        Decorator silences these expected 404s to avoid console spam.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dict containing calendar data or empty dict if unavailable
        """
        ticker = self._fetch_ticker(symbol)
        try:
            if hasattr(ticker, '_calendar'):
                return ticker._calendar or {}
            return ticker.calendar or {}
        except Exception as e:
            print(f"Warning: Error fetching calendar for {symbol}: {str(e)}")
            return {}