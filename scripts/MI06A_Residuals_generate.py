#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 16:24:04 2020

@author: Alan
"""

from MI_Libraries import *
from MI_Classes import ResidualsGenerate

# Default parameters
if len(sys.argv) != 3:
    print('WRONG NUMBER OF INPUT PARAMETERS! RUNNING WITH DEFAULT SETTINGS!\n')
    sys.argv = ['']
    sys.argv.append('Age')  # target
    sys.argv.append('test')  # fold

# Options
debug_mode = False

# Compute results
Residuals_Generate = ResidualsGenerate(target=sys.argv[1], fold=sys.argv[2])
Residuals_Generate.generate_residuals()
Residuals_Generate.save_residuals()

# Exit
print('Done.')
sys.exit(0)