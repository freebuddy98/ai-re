#!/usr/bin/env python3
"""
NLU Service Runner

Simple script to run the NLU service.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from nlu_service import main

if __name__ == "__main__":
    main() 