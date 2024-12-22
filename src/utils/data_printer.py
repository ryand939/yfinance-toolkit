# src/utils/data_printer.py

from typing import Any, Dict, Optional
from datetime import datetime, date

class DictPrinter:
    """Utility for formatted printing of dictionary data with configurable styling"""
    
    def __init__(self, indent_size: int = 2, max_line_length: int = 100):
        self.indent_size = indent_size
        self.max_line_length = max_line_length

    def format_value(self, value: Any) -> str:
        if value is None:
            return "None"
        elif isinstance(value, (float, int)):
            if isinstance(value, float):
                return f"{value:.4f}"
            return str(value)
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, bool):
            return str(value)
        return str(value)

    def print_dict(self, data: Dict[str, Any], title: Optional[str] = None) -> None:
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        
        self._print_dict_content(data)

    def _print_dict_content(self, data: Dict[str, Any], level: int = 0) -> None:
        indent = "-" * (level * self.indent_size)
        
        max_key_length = max(len(str(k)) for k in data.keys()) + 3
        
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{indent}{str(key)}:")
                self._print_dict_content(value, level + 1)
            else:
                formatted_value = self.format_value(value)
                padding = " " * (max_key_length - len(str(key)))
                print(f"{indent}{str(key)}{padding}: {formatted_value}")


def print_data(data: Dict[str, Any], title: Optional[str] = None, indent: int = 2) -> None:
    """
    Convenience function for printing dictionary data.
    
    Args:
        data: Dictionary to print
        title: Optional title for the output
        indent: Number of spaces for indentation
    """
    printer = DictPrinter(indent_size=indent)
    printer.print_dict(data, title)