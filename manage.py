#!/usr/bin/env python
import os
from ctypes import CDLL
import sys


CDLL(r"C:\Users\silah\miniconda3\envs\livestock360\Library\bin\gdal.dll")
CDLL(r"C:\Users\silah\miniconda3\envs\livestock360\Library\bin\geos_c.dll")

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'livestock360_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
