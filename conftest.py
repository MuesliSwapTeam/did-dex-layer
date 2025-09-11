# conftest.py - pytest configuration file
import sys
import os

# Add src directory to Python path for testing
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Also add the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
