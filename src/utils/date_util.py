
# src/utils/date_util.py
from datetime import date, datetime
import numpy as np
import pandas as pd
from typing import Union

class DateNormalizer:
    """
    Utility for handling date normalization across multiple formats.

    Converts various date objects into standard Python date objects to ensure consistent date handling.

    """
    
    @staticmethod
    def normalize_date(dt: Union[datetime, pd.Timestamp, date, np.datetime64]) -> date:
        """
        Convert date-like object to a standard Python date object.
        
        Handles common date formats from various libraries:
        - Python datetime/date
        - Pandas Timestamp
        - NumPy datetime64
        
        Args:
            dt: Input date in any supported format
            
        Returns:
            date: Normalized date object
            
        Raises:
            ValueError: If input type cannot be converted to date
        """
        try:
            if isinstance(dt, (datetime, pd.Timestamp)):
                return dt.date()
            if isinstance(dt, date):
                return dt
            if isinstance(dt, np.datetime64):
                return pd.Timestamp(dt).date()
            raise ValueError(f"Unsupported date type: {type(dt)}")
        except Exception as e:
            raise ValueError(f"Date normalization failed for {dt} of type {type(dt)}: {str(e)}")
