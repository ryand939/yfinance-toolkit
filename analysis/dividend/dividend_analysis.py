# src\analysis\dividend\dividend_analysis.py

from typing import Tuple, Optional, Dict, List, Any
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from utils.date_util import DateNormalizer
from models.dividend_models import ExDividendPattern, DividendGapResult, DividendFrequency



class DividendPatternAnalyzer:
    """
    Core analysis logic for dividend patterns and predictions
    
    This class provides comprehensive analysis of dividend data relating to a ticker, including
    frequency detection, gap estimation between ex-dividend and dividend payment date, 
    and future payout date predictions.
    
    """

    # 3 year window to perform analysis
    RECENT_HISTORY_DAYS = 1095  

    # min number of intervals needed to perform analysis
    MIN_INTERVALS_REQUIRED = 2 

    # min number of recent ex-dividend date samples required for analysis
    MIN_SAMPLES_REQUIRED = 4 


    @staticmethod
    def analyze_dividend_frequency(dividends: pd.Series) -> Tuple[Optional[str], Optional[float]]:
        """
        Determines the frequency of ex-dividends (yes, EX-dividends) and the average intervals between them
        
        Analyzes historical ex-dividend dates to determine frequency and average interval between dates. 
        Focuses on recent history to handle cases where companies have changed their dividend patterns.

        Args:
            dividends: Time series of dividend payments with dates as index
            
        Returns:
            Tuple of (frequency, interval):
                - frequency: Payment category (monthly/quarterly/semi-annual/annual) or None
                - interval: Average days between payments or None
        """
        try:
            if dividends.empty or len(dividends) < 2:
                return None, None

            dates_array = dividends.index.values.astype('datetime64[D]')
            intervals = np.diff(dates_array).astype(float)
            valid_mask = (intervals > 0) & np.isfinite(intervals)
            valid_intervals = intervals[valid_mask]
            
            if len(valid_intervals) < DividendPatternAnalyzer.MIN_INTERVALS_REQUIRED:
                print(len(valid_intervals))
                return "insufficient_data", 0.0
                

            # focus on recent history to get frequency
            recent_cutoff = np.datetime64('now', 'D') - np.timedelta64(DividendPatternAnalyzer.RECENT_HISTORY_DAYS, 'D')
            recent_mask = dates_array >= recent_cutoff
            
            # get the avg interval over the recent history
            if np.sum(recent_mask[:-1]) >= DividendPatternAnalyzer.MIN_INTERVALS_REQUIRED:
                recent_intervals = np.diff(dates_array[recent_mask]).astype(float)
                avg_interval = float(np.median(recent_intervals[recent_intervals > 0]))
            else:
                avg_interval = float(np.median(valid_intervals))
                
            if not np.isfinite(avg_interval) or avg_interval <= 0:
                return "unknown", 0.0
                
            std_dev = float(np.std(valid_intervals, ddof=1))
            cv = std_dev / avg_interval if avg_interval > 0 else float('inf')
            
            # map the interval to freq using predefined ranges
            for (lower, upper), freq in DividendFrequency.INTERVAL_RANGES.items():
                if lower <= avg_interval < upper:
                    return freq, avg_interval
                    
            return "unknown", avg_interval

        except Exception as e:
            print(f"Error in frequency calculation: {str(e)}")
            return "unknown", 0.0




    @classmethod
    def analyze_dividend_gap(cls, calendar: Dict, avg_interval: Optional[float]) -> DividendGapResult:
        """
        Calculate usual rough gap between ex-dividend and payment dates.
        
        This method handles various edge cases as a result of Yahoo Finance's minimal dividend date data.
        Works best when the stock has calendar data, as that is the only consistent place to find dividend 
        payout dates. Once I have a single dividend payout date, I can get a pretty accurate gap. 
        If there is no calendar data, the returned gap is a complete guess.

        Args:
            calendar: Dictionary containing dividend calendar dates
            avg_interval: Average days between payments
            
        Returns:
            DividendGapResult containing:
                - gap_days: Expected number of days between ex-dividend and payment
                - confidence: Confidence level based on the boldness of estimation method
                - estimation_method: Method used to determine the gap
        """
        
    
        if calendar and isinstance(calendar, dict):
            div_date = calendar.get("Dividend Date")
            ex_date = calendar.get("Ex-Dividend Date")
            
            if all(isinstance(d, (date, datetime)) for d in [div_date, ex_date]):
                gap = (div_date - ex_date).days
                
                # If we have avg_interval and gap is larger than it,
                # this likely means we're seeing next cycle's dividend date
                if avg_interval and gap > avg_interval:
                    adjusted_gap = gap - int(avg_interval)
                    if 0 <= adjusted_gap <= 60:
                        return DividendGapResult(
                            gap_days=adjusted_gap,
                            confidence="moderate",
                            estimation_method="exdiv_predicted_direct_calendar"
                        )
                elif 0 <= gap <= 60:
                    return DividendGapResult(
                        gap_days=gap,
                        confidence="high",
                        estimation_method="direct_calendar"
                    )
                
                if avg_interval:
                    # Handle case where dividend date precedes ex-dividend date
                    estimated_last_ex_date = ex_date - timedelta(days=int(avg_interval))
                    calculated_gap = (div_date - estimated_last_ex_date).days
                    if 0 <= calculated_gap <= 60:
                        return DividendGapResult(
                            gap_days=calculated_gap,
                            confidence="moderate",
                            estimation_method="div_predicted_direct_calendar"
                        )
        
        # Hail Mary fallback - the gap is 1/3 the avg interval
        # i.e. For a quarterly paying dividend (~90 day interval), the gap is assumed to be 30
        #      For a monthly paying dividend (~30 day interval), the gap is assumed to be 10
        
        # Most of the time this is kinda accurate, but theres always that one stock 
        # with the most random unexpected gap imaginable. Sometimes you just can't win.
        return DividendGapResult(
            gap_days=min(34, (avg_interval // 3) if avg_interval else 34),
            confidence="low",
            estimation_method="default_fallback_guess"
        )




    @staticmethod
    def calculate_staleness_threshold(avg_interval: float, pattern: ExDividendPattern) -> float:
        """
        Calculate adaptive threshold for detecting stale dividend data.
        
        This method helps distinguish between cases where:
        1. A dividend payment is genuinely late/delayed
        2. Yahoo Finance hasn't updated their data yet
        
        Made specifically to handle the case where the last reported ex-dividend date for ENB.TO
        is 2024-08-30, which is approximately 113 days ago as of writing this. Is ENB.TO's latest dividend late, or is Yahoo's data outdated?
        ENB.TO typically has a ~90 day interval, and their history shows they are extremely consistent with their dividend dates.
        So they are given very little tolerance before assuming the last payment is late, vs considering Yahoo's data STALE. 

        Adjusts tolerance based on:
        - Payment frequency (longer intervals get more tolerance)
        - Historical consistency (more consistent patterns get less tolerance)
         
        Args:
            avg_interval: Average days between payments
            pattern: Historical pattern metrics
            
        Returns:
            float: Multiplier threshold (i.e., 1.1 means 10% tolerance)
        """

        # longer payment intervals get more tolerance
        base_threshold = 1.2 if avg_interval >= 60 else 1.1
        
        # if the pattern is usually consistent (low std), give less tolerance
        variance_factor = 1 if pattern.std_dev_days < 2 else \
                         1.0 if pattern.std_dev_days < 4 else 1.1
                         
        
        return base_threshold * variance_factor





    @classmethod
    def analyze_ex_dividend_patterns(cls, dividends: pd.Series) -> ExDividendPattern:
        """ 
        Function that analyzes/calculates historical data on dividends (really ex-div, since yFinance only gives historical ex-div data for some reason).
        This provides more data when we are trying to predict dates (like last div payout date) that yFinance doesn't provide.
         
        Args:
            dividends: Historical ex-dividend payment series
            
        Returns:
            ExDividendPattern containing statistical metrics about payment timing
        """
        
        try:
            if dividends.empty:
                return ExDividendPattern(0, 0, 0, 0)
                
            recent_cutoff = pd.Timestamp.now() - pd.Timedelta(days=DividendPatternAnalyzer.RECENT_HISTORY_DAYS)
            dates_index = pd.DatetimeIndex(dividends.index).tz_localize(None)
            recent_dividends = dividends[dates_index >= recent_cutoff]
            
            if len(recent_dividends) < DividendPatternAnalyzer.MIN_SAMPLES_REQUIRED:
                if len(dividends) < DividendPatternAnalyzer.MIN_SAMPLES_REQUIRED:
                    return ExDividendPattern(0, 0, 0, 0)
                recent_dividends = dividends
            
            days = np.array([DateNormalizer.normalize_date(d).day 
                           for d in recent_dividends.index])
            
               
            return ExDividendPattern(
                mean_day_of_month=float(np.mean(days)),
                std_dev_days=float(np.std(days, ddof=1)),
                min_day=int(np.min(days)),
                max_day=int(np.max(days)))
            
        except Exception as e:
            print(f"Pattern analysis failed: {str(e)}")
            return ExDividendPattern(0, 0, 0, 0)




    @classmethod
    def predict_future_dates(cls, gap_days: int, avg_interval: float, last_ex_date: Optional[date],
            calendar: Optional[Dict] = None, pattern: Optional[ExDividendPattern] = None,
            payout_timing: str = DividendFrequency.QUARTERLY) -> Optional[List[str]]:
        """
        Predict future dividend payment dates for 1+ year period. 
        
        Args:
            gap_days: Days between ex-dividend and payment
            avg_interval: Average days between payments
            last_ex_date: Last known ex-dividend date
            calendar: Optional upcoming dividend calendar
            pattern: Historical timing patterns
            payout_timing: Expected dividend frequency
            
        Returns:
            List of ISO format predicted payment dates or None if insufficient data
        """

        # return a minimum of one year, but its ok to go beyond that
        num_loops = 14 if payout_timing == DividendFrequency.MONTHLY else 6
        if not last_ex_date or avg_interval <= 0:
            return None
            
        future_dates = []
        today = date.today()
        
        
        # Check calendar for guaranteed next divident payout date if available
        if calendar and isinstance(calendar, dict):
            div_date = calendar.get("Dividend Date")
            ex_date = calendar.get("Ex-Dividend Date")
            
            if isinstance(div_date, (date, datetime, pd.Timestamp)) and \
            isinstance(ex_date, (date, datetime, pd.Timestamp)):
                
                div_date = DateNormalizer.normalize_date(div_date)
                ex_date = DateNormalizer.normalize_date(ex_date)
                
                if div_date >= today:
                    future_dates.append(div_date.isoformat())
                    last_known_date = div_date
                    
                    # project remaining dates starting with confirmed next date
                    for i in range(1, num_loops):
                        next_date = last_known_date + timedelta(days=int(round(avg_interval)))
                        future_dates.append(next_date.isoformat())
                        last_known_date = next_date
                        
                    return future_dates
        
        # begin projection from last ex-dividend date if no confirmed date
        last_known_date = last_ex_date
        
        for i in range(1, num_loops + 1):
            # project NEXT ex-dividend date
            next_ex = last_known_date + timedelta(days=int(round(avg_interval * i)))
            
            # payout will likely be gap_days AFTER the ex-dividend date
            next_payout = next_ex + timedelta(days=gap_days)
            
            # ensure it is a future date, thats the whole point!
            if next_payout >= today: 
                future_dates.append(next_payout.isoformat())
                
        return future_dates if future_dates else None






    @staticmethod
    def get_latest_ex_date(info: Dict[str, Any],
                           calendar: Dict,
                           dividends: pd.Series) -> Optional[str]:
        """

            
        Get most recent ex-dividend date using multiple fallback sources.
        
        Attempts to get the last ex-dividend date from 3 possible sources:
        1. Calendar data (always most reliable)
        2. Stock info dict 'exDividendDate'
        3. Historical dividend series - gives ex-dividend dates for some reason but it works in this case

        Args:
            info: Stock information dictionary
            calendar: Calendar data with upcoming dates
            dividends: Historical dividend series
            
        Returns:
            ISO format date string or None if no valid date found
        """
        
        # try calendar first for best data
        if calendar and isinstance(calendar, dict):
            cal_ex_date = calendar.get("Ex-Dividend Date")
            if isinstance(cal_ex_date, date):
                return cal_ex_date.isoformat()
        
        # next try info dict for possible date
        ex_div_timestamp = info.get('exDividendDate')
        if ex_div_timestamp:
            try:
                ex_date = datetime.fromtimestamp(ex_div_timestamp, tz=timezone.utc).date()
                return ex_date.isoformat()
            except Exception as e:
                print(f"Failed to parse exDividendDate: {e}")
        
        # fallback to the (ex-)dividends  list and take the latest
        if not dividends.empty:
            return dividends.index[-1].date().isoformat()
        
        return None
    




    @staticmethod
    def get_last_dividend_info(dividends: pd.Series, calendar: Dict, gap_days: int,
                               avg_interval: float, pattern: ExDividendPattern,
                               staleness_threshold: float) -> Dict[str, Optional[float | str]]:
        """
        
        Get the date and dollar amount for the last dividend payout. The date is a few days off in some cases.
        To my knowledge, yFinance does not provide a consistent way to find the last dividend date, so we are 
        forced to estimate much of the time.


        Uses the following methods to estimate the last dividend payout date:
        1. Direct from calendar data (best case scenario)
        2. Last given ex-dividend date plus typical gap
            - Check if estimated date makes sense and return, or
            - Adjust final date forward or backward if it is in the future or it is too old
 
        Args:
            dividends: Historical dividend series
            calendar: Dividend calendar data
            gap_days: Ex-dividend to payment gap
            avg_interval: Average days between payments
            pattern: Historical timing patterns
            staleness_threshold: Threshold for stale data detection
            
        Returns:
            Dictionary containing:
            - date: ISO format payment date
            - amount: Payment amount
            - estimation_method: Method used to determine values
        """
        try:
            if dividends.empty:
                return {
                    "date": None,
                    "amount": None,
                    "estimation_method": "no_dividend_history"
                }
            
            today = date.today()
            pattern_info = (f"[pattern: mean_day={pattern.mean_day_of_month:.1f}, "
                          f"std={pattern.std_dev_days:.1f}, "
                          f"threshold={staleness_threshold:.2f}]")
            
            last_ex_div = DateNormalizer.normalize_date(dividends.index[-1])
            last_amount = float(dividends.iloc[-1])
            
            if calendar and isinstance(calendar, dict):
                cal_div_date = calendar.get("Dividend Date")
                cal_ex_date = calendar.get("Ex-Dividend Date")
                
                if isinstance(cal_div_date, (date, datetime, pd.Timestamp)) and \
                   isinstance(cal_ex_date, (date, datetime, pd.Timestamp)):
                    
                    cal_div_date = DateNormalizer.normalize_date(cal_div_date)
                    cal_ex_date = DateNormalizer.normalize_date(cal_ex_date)
                    # days since the last dividend was paid out
                    days_since_cal = (today - cal_div_date).days
                    # if the number of days since the last payout is more than usual, 
                    # and a staleness_threshold to determine if this is uncharacteristic of them
                    if days_since_cal > avg_interval * staleness_threshold:
                        estimated_div_date = cal_div_date + timedelta(days=int(avg_interval))
                        if estimated_div_date <= today:
                            return {
                                "date": estimated_div_date.isoformat(),
                                "amount": last_amount,
                                "estimation_method": f"calendar_date_plus_one_interval"
                            }
                    # calendar data is JUST stale enough that it is exactly the last dividend data
                    elif cal_div_date < today:
                        return {
                            "date": cal_div_date.isoformat(),
                            "amount": last_amount,
                            "estimation_method": f"direct_from_calendar"
                        }
            
            # The estimated payout date is the last reported ex-div date + the usual gap
            estimated_payout = last_ex_div + timedelta(days=gap_days)

            # handle cases where estimated last div date is too old, predicted into the future, or just right
            days_since_estimated = (today - estimated_payout).days
            
            # case where estimated payout is one cycle too old 
            # the average payout interval is added to get the last dividend date
            if days_since_estimated > avg_interval * staleness_threshold:
                projected_date = estimated_payout + timedelta(days=int(avg_interval))
                if projected_date <= today:
                    return {
                        "date": projected_date.isoformat(),
                        "amount": last_amount,
                        "estimation_method": f"ex_dividend_plus_interval_projection"
                    }
                
            # case where the new date is now in the future 
            # retry with the second last ex-dividend date
            if estimated_payout > today or days_since_estimated > avg_interval * staleness_threshold:
                if len(dividends) > 1:
                    prev_ex_div = DateNormalizer.normalize_date(dividends.index[-2])
                    prev_amount = float(dividends.iloc[-2])
                    prev_estimated_payout = prev_ex_div + timedelta(days=gap_days)
                    
                    if prev_estimated_payout <= today:
                        return {
                            "date": prev_estimated_payout.isoformat(),
                            "amount": prev_amount,
                            "estimation_method": f"previous_ex_dividend_plus_gap"
                        }
            
            # case where the estimated last date is seemingly not too old or ahead of today's date
            # this is likely the last div date!
            if estimated_payout <= today:
                return {
                    "date": estimated_payout.isoformat(),
                    "amount": last_amount,
                    "estimation_method": f"ex_dividend_plus_gap_basic"
                }
            
            return {
                "date": None,
                "amount": None,
                "estimation_method": f"estimation_failed {pattern_info}"
            }
            
        except Exception as e:
            print(f"Dividend info calculation failed: {str(e)}")
            return {
                "date": None,
                "amount": None,
                "estimation_method": f"error_during_processing: {str(e)}"
            }

