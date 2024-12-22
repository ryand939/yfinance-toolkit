# src/models/dividend_models.py
from dataclasses import dataclass
from typing import Optional, Dict, ClassVar, Literal


@dataclass
class DividendFrequency:
    """
    Constants and utilities for dividend payment frequencies.
    
    Provides standardized frequency names, payment calculations,
    and interval ranges for analyzing dividend payment patterns.
    """
    
    # standardized frequency names
    MONTHLY: ClassVar[str] = "monthly"
    QUARTERLY: ClassVar[str] = "quarterly"
    SEMI_ANNUAL: ClassVar[str] = "semi-annual"
    ANNUAL: ClassVar[str] = "annual"
    
    # number of payments expected per year for each frequency
    PAYMENTS_PER_YEAR: ClassVar[Dict[str, int]] = {
        MONTHLY: 12,
        QUARTERLY: 4,
        SEMI_ANNUAL: 2,
        ANNUAL: 1
    }
    
    # typical day interval ranges to categorize frequency
    INTERVAL_RANGES: ClassVar[Dict[tuple[int, int], str]] = {
        (0, 35): MONTHLY,
        (35, 95): QUARTERLY,
        (95, 185): SEMI_ANNUAL,
        (185, float('inf')): ANNUAL
    }
    
    @classmethod
    def is_valid_frequency(cls, frequency: str) -> bool:
        """
        Validate if a frequency string matches known frequencies.
        
        Args:
            frequency: String to validate
            
        Returns:
            bool: True if frequency is valid
        """
        return frequency in cls.PAYMENTS_PER_YEAR
    
    @classmethod
    def get_payments_needed(cls, frequency: str) -> Optional[int]:
        """
        Get number of payments needed for a particular frequency.
        
        Args:
            frequency: Dividend payment frequency
            
        Returns:
            int: Number of payments per year or None if invalid
        """
        return cls.PAYMENTS_PER_YEAR.get(frequency)



@dataclass
class DividendGapResult:
    """
    Analysis result for gap between ex-dividend and payment dates.
    
    Tracks the calculated gap and the estimation method + confidence in estimation.
    """
    gap_days: int # number of days between ex-dividend date and dividend payout date
    confidence: Literal["high", "moderate", "low"] # confidence level based on estimation method
    estimation_method: str # specific method used to estimate the gap



@dataclass
class ExDividendPattern:
    """
    Statistical analysis of historical ex-dividend dates.
    
    Captures timing patterns to improve understanding of ex-dividend dates.
    """
    mean_day_of_month: float # average day of the month for ex-div to land on
    std_dev_days: float # standard deviation of dates in days
    min_day: int # earliest observed ex-div date
    max_day: int # latest observed ex-div date

