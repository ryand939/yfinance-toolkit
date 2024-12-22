from typing import Optional, List, Dict

def get_redundant_field(data: Dict, primary_key: str, backup_keys: List[str]
                        ) -> Optional[float]:
    
    """
    Extract numerical value with fallback options.
    
    Used for Yahoo Finance data where the same values exist under different aliases.
    Tries primary_key first, then each backup_key.
    
    Args:
        data: Dictionary to search
        primary_key: Preferred key to check first
        backup_keys: Alternative keys to try if primary fails
        
    Returns:
        float value if found, None if no valid value exists
    """
    if value := data.get(primary_key): return float(value)
    for key in backup_keys:
        if value := data.get(key):
            return float(value)
    return None