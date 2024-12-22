# src\analysis\dividend\dividend_calculations.py

from typing import Optional, Dict, Any, Tuple
import pandas as pd
from src.utils.get_redundant_field import get_redundant_field
from src.models.dividend_models import DividendFrequency



class DividendCalculator:
    """

    Handles all dividend-related calculations.

    """
    
    @staticmethod
    def calculate_dividend_rate(price: Optional[float], info: Dict[str, Any], dividends: pd.Series, frequency: Optional[str]
                                ) -> Tuple[Optional[float], str]:
        """
        Calculate a ticker's annual dividend rate.

        Tries the following methods to calculate depending on what data is available:
        1. Direct rate from stock info
        2. Price * Yield calculation
        3. Historical payment analysis based on frequency

        Args:
            price: Current stock price
            info: Stock information dictionary
            dividends: Historical dividend series
            frequency: Payment frequency (monthly, quarterly, etc.)
            
        Returns:
            Tuple of (rate, method):
                - rate: Annual dividend rate or None if calculation fails
                - method: String describing which calculation method was used
        """
        # Method 1: Direct from info if available
        if rate := info.get('dividendRate'):
            return float(rate), "direct_from_info"
            
        # Method 2: Price * Yield if available
        if price and (yield_value := get_redundant_field(info, "dividendYield", ["yield"])):
            return round(price * yield_value, 4), "price_and_yield_product"
            
        # Method 3 fallback hail mary: Calculate from history based on frequency
        if not dividends.empty and frequency is not None:
            if annual_rate := DividendCalculator._annualize_dividends(dividends.tail(12), frequency):
                return annual_rate, f"historical_{frequency}_calculation"


        return None, "failed_not_enough_data"




    @staticmethod
    def calculate_payout_ratio(info: Dict[str, Any], dividend_rate: Optional[float]
                               ) -> Tuple[Optional[float], str]:
        """
        Calculate the dividend payout ratio.
        
        Tries the following methods to calculate depending on what data is available:
        1. Direct ratio from stock info
        2. Dividend rate / EPS calculation
        3. Dividend rate / (Net Income / Shares Outstanding)
        
        Args:
            info: Stock information dictionary
            dividend_rate: Annual dividend rate
            
        Returns:
            Tuple of (ratio, method):
                - ratio: Payout ratio as decimal or None if calculation fails
                - method: String describing which calculation method was used
        """
        # Method 1: Direct ratio from stock info
        if ratio := info.get('payoutRatio'):
            return float(ratio), "direct_from_info"
            
        if not dividend_rate:
            return None, "no_dividend_rate"
        
        # Method 2: Dividend rate / EPS calculation
        if eps := info.get('trailingEps'):
            if eps != 0:
                return round(dividend_rate / eps, 4), "eps_based"

        # Method 3: Dividend rate / (Net Income / Shares Outstanding)  
        shares = info.get('sharesOutstanding')
        net_income = info.get('netIncome')
        
        if all([shares, net_income]) and shares != 0:
            net_income_per_share = net_income / shares
            if net_income_per_share != 0:
                return round(dividend_rate / net_income_per_share, 4), "income_based"
                
        return None, "failed_not_enough_data"




    @staticmethod
    def _annualize_dividends(recent_divs: pd.Series, frequency: str) -> Optional[float]:
        """
        Convert recent dividend payments to annual rate based on payment frequency.
        
        Uses recent payments to constitute one year:
        - Monthly: Sum of last 12 payments
        - Quarterly: Sum of last 4 payments
        - Semi-annual: Sum of last 2 payments
        - Annual: Last payment
        
        Args:
            recent_divs: Recent dividend payment series
            frequency: Payment frequency (monthly, quarterly, etc.)
            
        Returns:
            float: Annualized dividend rate or None if invalid frequency
        """
        if not DividendFrequency.is_valid_frequency(frequency):
            return None
            
        n_payments = DividendFrequency.get_payments_needed(frequency)
        recent_year = recent_divs.tail(n_payments)
        
        if len(recent_year) > 0:
            annual_rate = float(recent_year.sum() * (n_payments / len(recent_year)))
            return round(annual_rate, 4)
        
        return None
