import sys
import os

os.makedirs('./_internal/libs', exist_ok=True)
sys.path.insert(0, './_internal/libs')
del sys, os
