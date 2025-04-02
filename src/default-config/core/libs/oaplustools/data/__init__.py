# data __init__

from oaplustools.package import LazyModuleLoader as _LazyModuleLoader

# Lazy loading modules
database = _LazyModuleLoader('oaplustools.data.database')
updaters = _LazyModuleLoader('oaplustools.data.updaters')
faker = _LazyModuleLoader('oaplustools.data.faker')
imagetools = _LazyModuleLoader('oaplustools.data.imagetools')
advanced_imagetools = _LazyModuleLoader('oaplustools.data.advanced_imagetools')
compressor = _LazyModuleLoader('oaplustools.data.compressor')

# Define __all__ to limit what gets imported with 'from <package> import *'
__all__ = ['database', 'updaters', 'faker', 'imagetools', 'advanced_imagetools', 'compressor']

# Dynamically add exports from _direct_functions
from oaplustools.data._direct_functions import *

# Update __all__ with the public members from _direct_functions and clean up globals
for name in list(globals()):
    if name.startswith('_') and not (name.startswith('__') and name.endswith('__')):
        # Remove private attributes from globals
        del globals()[name]
    else:
        # Add public attributes to __all__
        __all__.append(name)
del name
