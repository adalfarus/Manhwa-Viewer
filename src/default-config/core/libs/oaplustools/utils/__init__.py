# utils __init__

from oaplustools.package import LazyModuleLoader as _LazyModuleLoader

# Lazy loading modules
genpass = _LazyModuleLoader('oaplustools.utils.genpass')
dummy = _LazyModuleLoader('oaplustools.utils.dummy')
hasher = _LazyModuleLoader('oaplustools.utils.hasher')

# Define __all__ to limit what gets imported with 'from <package> import *'
__all__ = ['genpass', 'dummy', 'hasher']

# Dynamically add exports from _direct_functions
from oaplustools.utils._direct_functions import *

# Update __all__ with the public members from _direct_functions and clean up globals
for name in list(globals()):
    if name.startswith('_') and not (name.startswith('__') and name.endswith('__')):
        # Remove private attributes from globals
        del globals()[name]
    else:
        # Add public attributes to __all__
        __all__.append(name)
del name
