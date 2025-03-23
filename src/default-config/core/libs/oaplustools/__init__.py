# oaplustools __init__
__version__ = "1.4.8.4"


from oaplustools.package import LazyModuleLoader as _LazyModuleLoader

# Lazy loading modules
io = _LazyModuleLoader('oaplustools.io')
data = _LazyModuleLoader('oaplustools.data')
utils = _LazyModuleLoader('oaplustools.utils')
web = _LazyModuleLoader('oaplustools.web')
package = _LazyModuleLoader('oaplustools.package')

# Define __all__ to limit what gets imported with 'from <package> import *'
__all__ = ['io', 'data', 'utils', 'web', 'package']

# Dynamically add exports from _direct_functions
from oaplustools._direct_functions import *

# Update __all__ with the public members from _direct_functions and clean up globals
for name in list(globals()):
    if name.startswith('_') and not (name.startswith('__') and name.endswith('__')):
        # Remove private attributes from globals
        del globals()[name]
    else:
        # Add public attributes to __all__
        __all__.append(name)
del name
