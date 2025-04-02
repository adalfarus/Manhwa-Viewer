# package __init__

from oaplustools.package._direct_functions import LazyModuleLoader as _LazyModuleLoader

# Lazy loading modules
timid = _LazyModuleLoader('oaplustools.package.timid')
argumint = _LazyModuleLoader('oaplustools.package.argumint')

# Define __all__ to limit what gets imported with 'from <package> import *'
__all__ = ['timid', 'argumint']

# Dynamically add exports from _direct_functions
from oaplustools.package._direct_functions import *

# Update __all__ with the public members from _direct_functions and clean up globals
for name in list(globals()):
    if name.startswith('_') and not (name.startswith('__') and name.endswith('__')):
        # Remove private attributes from globals
        del globals()[name]
    else:
        # Add public attributes to __all__
        __all__.append(name)
del name
