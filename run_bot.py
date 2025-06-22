#!/usr/bin/env python

"""
Runner script for E7gz Bot
This script ensures the bot is run with the correct Python module path
"""

import os
import sys

# Add the current directory to Python path to make src package importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function from the bot module
from src.bot import main

if __name__ == '__main__':
    main()