import math
import sys

class DummyBase:
    def __init__(*args, **kwargs):
        pass
        
    # Attribute dunder methods
    def __call__(self, *args, **kwargs):
        return self
    def __getattr__(self, *args, **kwargs):
        return self
    def __setattr__(self, key, value):
        return self
    def __delattr__(self, item):
        return None
        
    # Iter, index and with keyword dunder Methods
    def __iter__(self):
        yield
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        return True
    def __getitem__(self, item):
        return self
    def __setitem__(self, key, new_value):
        return
    def __delitem__(self, key):
        return None
        
    # Type dunder methods
    def __int__(self):
        return int()
    def __float__(self):
        return float()
        
    # Function dunder methods
    def __len__(self):
        return int()
    def __abs__(self):
        return self
    def __invert__(self):
        return self
    def __round__(self):
        return self
    def __trunc__(self):
        return self
        
    # Unary operators (-x, +x, ~x)
    def __pos__(self):
        return self
    def __neg__(self):
        return self
        
    # Operators (+, -, /, //, %, &, @, <<, >>, ~, *, **, |, ^)
    def __add__(self, other):
        return self
    def __radd__(self, other):
        return self
    def __sub__(self, other):
        return self
    def __rsub__(self, other):
        return self
    def __mul__(self, other):
        return self
    def __rmul__(self, other):
        return self
    def __div__(self, other):
        return self
    def __rdiv__(self, other):
        return self
    def __floordiv__(self, other):
        return self
    def __rfloordiv__(self, other):
        return self
    def __truediv__(self, other):
        return self
    def __rtruediv__(self, other):
        return self
    def __mod__(self, other):
        return self
    def __rmod__(self, other):
        return self
    def __divmod__(self, other):
        return self
    def __rdivmod__(self, other):
        return self
    def __pow__(self,n):
        return self
    def __rpow__(self, n):
        return self
    def __lshift__(self, other):
        return self
    def __rlshift__(self, other):
        return self
    def __rshift__(self, other):
        return self
    def __rrshift__(self, other):
        return self
    def __and__(self, other):
        return self
    def __rand__(self, other):
        return self
    def __or__(self, other):
        return self
    def __ror__(self, other):
        return self
    def __xor__(self, other):
        return self
    def __rxor__(self, other):
        return self
    def __format__(self, format_str: str = ""):
        return ""
        
class Dummy2(DummyBase):
    # Dummy for Python2
    def __init__(*args, **kwargs):
        if not sys.version[0] == "2": # EnvironmentError
            raise RuntimeError("Please only use Dummy2 for python2")
    def __long__(self): # For compatiblity with python2
        return self
    def __oct__(self):
        return self
    def __hex__(self):
        return self
    def __coerce__(self, other):
        return self
    def __unicode__(self):
        return u''
    def __nonzero__(self):
        return False
    def next(self):
        raise StopIteration
        
class Dummy3(DummyBase):
    # Dummy for Python3
    def __init__(*args, **kwargs):
        if not sys.version[0] == "3": # EnvironmentError
            raise RuntimeError("Please only use Dummy3 for python3")
            
    #def __next__(self): # Not needed
    #    raise StopIteration

    def __index__(self):
        return int()

    def __hash__(self):
        return int()

def local_test():
    try:
        dummy = Dummy3()
        dummy.attr.func("", "")
        del dummy[1]
        reversed(dummy)
        print("" in dummy)
        print(dummy["HELP"])
        print(dummy.keys())
        dummy.keys = ""
        print(dummy.keys + dummy)
        print(+dummy)
        print(-dummy)
        print(hash(dummy))
        print(abs(dummy))
        ~dummy
        round(dummy)
        import math
        print(math.ceil(dummy))
        dummy << dummy
        dummy += 1
        intt = 1
        intt *= dummy
        complex(dummy)
        oct(dummy)
        math.trunc(dummy)
        repr(dummy)
        print(bytes(dummy))
        print(format(dummy, ""))
        dummy.format()
        if dummy:
            print(True)
        else:
            print(False)
        for x in dummy:
            print("HELLO")
        type(dummy)
        print(dummy, str(dummy), int(dummy), list(dummy), tuple(dummy), float(dummy))
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
