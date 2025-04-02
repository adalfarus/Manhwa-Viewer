import random
from typing import Optional, List, Callable


class UM:
    """
    All the methods in this class are designed to change a given list
    so that all elements aren't at the same index as before and don't
    have the same neighbors as before. Some like umreihen have a second
    to make it hard to get the original input from the output.
    
    Generally a higher number means the function has improved by either
    the output quality or the efficiency.
    """
    @staticmethod
    def umreihen(num_lst: list, depth: int) -> list:
        if not num_lst:  # Check if the list is empty
            return []
        
        curr_num_lst = num_lst
        for _ in range(depth):
            new_num_lst = []
            for num in curr_num_lst:
                if num != 0:
                    index = num % len(curr_num_lst)
                    new_num_lst.append(curr_num_lst[index - 1 if index > 0 else index])
                else:
                    new_num_lst.append(curr_num_lst[num])
            curr_num_lst = new_num_lst
        return curr_num_lst
        
    @staticmethod
    def umreihenTWO(num_lst: list, depth: int) -> list:
        if not num_lst:  # Check if the list is empty
            return []

        curr_num_lst = num_lst
        for _ in range(depth):
            new_num_lst, index = [], 0
            while len(curr_num_lst) > 0:
                num = curr_num_lst[0]
                if num != 0:
                    index = num % len(curr_num_lst)
                    new_num_lst.append(curr_num_lst.pop(index - 1 if index > 0 else index))
                else:
                    new_num_lst.append(curr_num_lst[num])
                index += 1
            curr_num_lst = new_num_lst
        return curr_num_lst
    
    @staticmethod
    def umreihenTHREE(num_lst: list, depth: int) -> list:
        if not num_lst:  # Check if the list is empty
            return []

        curr_num_lst = num_lst[:]
        print(len(num_lst))
        for _ in range(depth):
            new_num_lst, index = [], 0
            while len(curr_num_lst) > 1:
                #print(index, num_lst, curr_num_lst, _)
                num = num_lst[index]
                if num != 0:
                    lst_index = num % len(curr_num_lst)
                    new_num_lst.append(curr_num_lst.pop(lst_index - 1 if lst_index > 0 else lst_index))
                else:
                    new_num_lst.append(curr_num_lst.pop(index))
                index += 1
            new_num_lst.insert(0, curr_num_lst.pop(0))
            curr_num_lst = new_num_lst
            num_lst = curr_num_lst[:]
        return curr_num_lst
    
    @staticmethod
    def umreihenFOUR(num_lst: list, depth: int) -> list:
        if not num_lst:  # Check if the list is empty
            return []

        curr_num_lst = num_lst[:]
        #print(len(num_lst))
        for _ in range(depth):
            new_num_lst, index = [curr_num_lst.pop(-1)], 0
            while len(curr_num_lst) > 0:
                num = num_lst[index]
                if num != 0:
                    lst_index = num % len(curr_num_lst)
                    new_num_lst.append(curr_num_lst.pop(lst_index - 1 if lst_index > 0 else lst_index))
                else:
                    new_num_lst.append(curr_num_lst.pop(index))
                index += 1
            curr_num_lst = new_num_lst
            num_lst = curr_num_lst[:]
        return curr_num_lst
    
    @staticmethod
    def umsplitten(num_lst: list, width: int = 2) -> Optional[list]:
        try:
            raise DeprecationWarning("This function is deprecated, please use umsplittedTWO or umsplittenCH")
        except Exception as e:
            print("Exec Error:", e)
            return # This doesn't work
        if len(num_lst) // 2 < width or len(num_lst) % 2 != 0: # Otherwise pairs don't match
            return None
            
        split_point = len(num_lst) // width
        pairs = []
        
        for i, x in enumerate(num_lst[split_point:]):
            pairs.append([x, num_lst[((x + width) % len(num_lst)) - 1]])
            
        lst_1, lst_2 = zip(*pairs)
        return lst_1 + lst_2
        
    @staticmethod
    def umsplittenCH(num_lst: list) -> Optional[list]:
        if len(num_lst) % 2 != 0:  # Ensure the list has an even number of elements
            return None

        split_point = len(num_lst) // 2
        lst_1 = num_lst[:split_point]
        lst_2 = num_lst[split_point:]

        result = []
        for a, b in zip(lst_1, lst_2):
            result.extend([a, b])

        return result
        
    @staticmethod
    def umsplittenTWO(num_lst: list, width: int = 2) -> Optional[list]:
        if width > len(num_lst) // 2:  # or len(num_lst) % 2 != 0:
            return None

        result = []
        for start in range(width):
            result.extend(num_lst[start::width])

        return result
        
    @staticmethod
    def umsetzen(lst: list) -> list:
        """
        The umsetzen function is designed to 
        move each element to a new spot and 
        make sure they don't have the same
        neighbor as before.
        """
        Dummy = type('Dummy', (object,), {'__init__': lambda self, *args, **kwargs: None,
                                          '__call__': lambda self, *args, **kwargs: self,
                                          '__getattr__': lambda self, *args, **kwargs: self})

        new_lst = []
        for x in range(0, len(lst), 6):
            for dent in [0, 2, 4, 1, 5, 3]:
                if x + dent < len(lst):
                    new_lst.append(lst[x + dent])
                    lst[x + dent] = Dummy()
                else:
                    print()
                    filtered_list = [element for element in lst if not isinstance(element, Dummy)]
                    new_lst.insert(0, filtered_list[0])
        #if len(new_lst) < len(lst):
        #    pass # Fix
            #for x, y in zip(lst[len(new_lst):], [0, 2, 4, 1, 5, 3][:len(lst) - len(new_lst)]):
            #    new_lst.append(x
        return new_lst


def hashed_old(input_str: str, length: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    original_length = len(input_str)
    if original_length > length: return "Please only input inputs shorter than length"
    elif not isinstance(input_str, str): return "Please only pass strings as input"
    filled_input = input_str.ljust(length, "0")
    debug_print("Filled: " + filled_input)
    seed, input_lst = input_str, list(input_str)
    shuffled_input = ""
    for i, char in enumerate(filled_input):
        if char == "0":
            random.seed(seed)
            rand_char = random.choice(input_lst)
            char = rand_char
            seed_lst = list(seed)
            random.shuffle(seed_lst)
            seed = ''.join(seed_lst)
        shuffled_input += chr(ord(char) + original_length // i if i % 2 == 0 and i != 0 else original_length * i)
    debug_print("Shuffled: " + shuffled_input)
    shuffled_length = len(shuffled_input)
    split_lst, i = [shuffled_input], 1
    param = original_length
    while len(split_lst) != shuffled_length:
        debug_print(f"Split_lst: {len(split_lst)}/{shuffled_length}")
        param = max(1, param // i if i % 2 == 0 else param * i)
        debug_print("Param: ", param)
        i2 = -1
        while i2+1 < len(split_lst):
            i2 += 1
            element = split_lst[i2]
            debug_print(f"Element: {element}, {len(element)}")
            if len(element) <= param:
                continue
            debug_print(f"{element} -> \n1. {element[:param]},\n2. {element[param:]}")
            str1, str2 = element[:param], element[param:]
            split_lst[i2] = str1
            split_lst.insert(i2+1, str2)
        random.seed(param)
        random.shuffle(split_lst)
        i += 1
    return ''.join(split_lst)


def hashed(input_str: str, length: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    original_length = len(input_str)
    if original_length > length: return "Please only input inputs shorter than length"
    elif not isinstance(input_str, str): return "Please only pass strings as input"
    filled_input = input_str.ljust(length, "0")
    debug_print("Filled: " + filled_input)
    seed, input_lst = input_str, list(input_str)
    shuffled_input = ""
    ord_lst = [ord(x) + original_length for x in input_str]
    print(ord_lst)
    for i, char in enumerate(filled_input):
        if char == "0":
            random.seed(seed)
            rand_char = random.choice(input_lst)
            char = rand_char
            seed_lst = list(seed)
            random.shuffle(seed_lst)
            seed = ''.join(seed_lst)
        shuffled_input += chr(ord(char) + ord_lst[i % original_length] // i if i % 2 == 0 and i != 0 else ord_lst[i % original_length] * i)
    debug_print("Shuffled: " + shuffled_input)
    shuffled_length = len(shuffled_input)
    split_lst, i = [shuffled_input], 1
    param = original_length
    while len(split_lst) != shuffled_length:
        debug_print(f"Split_lst: {len(split_lst)}/{shuffled_length}")
        param = ord_lst[i % original_length] = max(1, ord_lst[i % original_length] // i if i % 2 == 0 else ord_lst[i % original_length] * i)
        debug_print("Param: ", param)
        i2 = -1
        while i2+1 < len(split_lst):
            i2 += 1
            element = split_lst[i2]
            debug_print(f"Element: {element}, {len(element)}")
            if len(element) <= param:
                continue
            debug_print(f"{element} -> \n1. {element[:param]},\n2. {element[param:]}")
            str1, str2 = element[:param], element[param:]
            split_lst[i2] = str1
            split_lst.insert(i2+1, str2)
        random.seed(param)
        random.shuffle(split_lst)
        i += 1
    return ''.join(split_lst)


def hashed_LS(input_str: str, length: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    def order_lst(original_length, input, seed1=200, seed2=30):
        ord_lst = [ord(x) + (i + 1) * (ord(x) + i) * (2 if x.islower() else 3 if x.isupper() else 1) for i, x in enumerate(input)]
        ord_lst = [str(int(original_length + sum(val * (ord(x) / 10 if i == j else ord(x) / 5) for j, x in enumerate(input)))) for i, val in enumerate(ord_lst)]
        # Splitting and reducing the values
        new_ord_lst = []
        for element in ord_lst:
            split_index = len(element) // 2  # Simplified splitting index
            new_ord_lst.extend([element[:split_index], element[split_index:]])
        # Random selection and reduction
        random.seed(input)
        final_ord_lst = []
        for _ in range(len(ord_lst)):
            choice = random.choice(new_ord_lst)
            number = int(choice)
            new_ord_lst.remove(choice)
            reduced_number = number if number < seed1 else int(number // ((seed1 / number) * seed2))
            final_ord_lst.append(reduced_number)
        return final_ord_lst
    def reduce_lst(lst):
        import math

        # Apply logarithmic scaling and then modular reduction
        reduced_lst = [int(math.log(x + 1)) % 100 for x in lst]

        return reduced_lst
    original_length = len(input_str)
    if original_length > length: return "Please only input inputs shorter than length"
    elif not isinstance(input_str, str): return "Please only pass strings as input"
    filled_input = input_str.ljust(length, "0")
    debug_print("Filled: " + filled_input)
    seed, input_lst = input_str, list(input_str)
    shuffled_input = ""
    ord_lst = order_lst(original_length, input_str) #[ord(x) + original_length for x in input]
    debug_print("Ord List: ", ord_lst)
    ord_lst = reduce_lst(ord_lst)
    for i, char in enumerate(filled_input):
        if char == "0":
            random.seed(seed)
            rand_char = random.choice(input_lst)
            char = rand_char
            seed_lst = list(seed)
            random.shuffle(seed_lst)
            seed = ''.join(seed_lst)
        shuffled_input += chr(ord(char) + ord_lst[i % original_length] // i if i % 2 == 0 and i != 0 else ord_lst[i % original_length] * i)
    debug_print("Shuffled: " + shuffled_input)
    shuffled_length = len(shuffled_input)
    split_lst, i = [shuffled_input], 1
    param = original_length
    while len(split_lst) != shuffled_length:
        debug_print(f"Split_lst: {len(split_lst)}/{shuffled_length}")
        param = ord_lst[i % original_length] = max(1, ord_lst[i % original_length] // i if i % 2 == 0 else ord_lst[i % original_length] * i)
        debug_print("Param: ", param)
        i2 = -1
        while i2+1 < len(split_lst):
            i2 += 1
            element = split_lst[i2]
            debug_print(f"Element: {element}, {len(element)}")
            if len(element) <= param:
                continue
            debug_print(f"{element} -> \n1. {element[:param]},\n2. {element[param:]}")
            str1, str2 = element[:param], element[param:]
            split_lst[i2] = str1
            split_lst.insert(i2+1, str2)
        random.seed(param)
        random.shuffle(split_lst)
        i += 1
    return ''.join(split_lst)


def hashed_LS2(input_str: str, length: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    def order_lst(original_length, input, seed1=200, seed2=30):
        ord_lst = [ord(x) + (i + 1) * (ord(x) + i) * (2 if x.islower() else 3 if x.isupper() else 1) for i, x in enumerate(input)]
        ord_lst = [str(int(original_length + sum(val * (ord(x) / 10 if i == j else ord(x) / 5) for j, x in enumerate(input)))) for i, val in enumerate(ord_lst)]
        # Splitting and reducing the values
        new_ord_lst = []
        for element in ord_lst:
            split_index = len(element) // 2  # Simplified splitting index
            new_ord_lst.extend([element[:split_index], element[split_index:]])
        # Random selection and reduction
        random.seed(input)
        final_ord_lst = []
        for _ in range(len(ord_lst)):
            choice = random.choice(new_ord_lst)
            number = int(choice)
            new_ord_lst.remove(choice)
            reduced_number = number if number < seed1 else int(number // ((seed1 / number) * seed2))
            final_ord_lst.append(reduced_number)
        return final_ord_lst
    def reduce_lst(lst):
        import math

        # Apply logarithmic scaling and then modular reduction
        reduced_lst = [int(math.log(x + 1)) % 100 for x in lst]

        return reduced_lst
    original_length = len(input_str)
    if original_length > length: return "Please only input inputs shorter than length"
    elif not isinstance(input_str, str): return "Please only pass strings as input"
    filled_input = input_str.ljust(length, "0")
    debug_print("Filled: " + filled_input)
    seed, input_lst = input_str, list(input_str)
    shuffled_input = ""
    ord_lst = order_lst(original_length, input_str) #[ord(x) + original_length for x in input]
    debug_print("Ord List: ", ord_lst)
    #ord_lst = reduce_lst(ord_lst)
    for i, char in enumerate(filled_input):
        if char == "0":
            random.seed(seed)
            rand_char = random.choice(input_lst)
            char = rand_char
            seed_lst = list(seed)
            random.shuffle(seed_lst)
            seed = ''.join(seed_lst)
        shuffled_input += chr(ord(char) + ord_lst[i % original_length] // i if i % 2 == 0 and i != 0 else ord_lst[i % original_length] * i)
    debug_print("Shuffled: " + shuffled_input)
    shuffled_length = len(shuffled_input)
    split_lst, i = [shuffled_input], 1
    param = original_length
    while len(split_lst) != shuffled_length:
        debug_print(f"Split_lst: {len(split_lst)}/{shuffled_length}")
        param = ord_lst[i % original_length] = max(1, ord_lst[i % original_length] // i if i % 2 == 0 else ord_lst[i % original_length] * i)
        debug_print("Param: ", param)
        i2 = -1
        while i2+1 < len(split_lst):
            i2 += 1
            element = split_lst[i2]
            debug_print(f"Element: {element}, {len(element)}")
            if len(element) <= param:
                continue
            debug_print(f"{element} -> \n1. {element[:param]},\n2. {element[param:]}")
            str1, str2 = element[:param], element[param:]
            split_lst[i2] = str1
            split_lst.insert(i2+1, str2)
        random.seed(param)
        random.shuffle(split_lst)
        i += 1
    return ''.join(split_lst)


def hashed_latest(input_str: str, length: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    original_length = len(input_str)
    
    if original_length > length:
        return "Please only input strings shorter than length"
    elif not isinstance(input_str, str):
        return "Please only pass strings as input"
        
    filled_input = input_str.ljust(length, "0") # Buffer input_str to length
    debug_print("Filled input string: " + filled_input)
    
    seed, input_lst = input_str, list(input_str)
    shuffled_input = ""
    ord_lst = UM.umreihenFOUR([ord(x) + original_length for x in input_str], length)
    debug_print("O.R.D. lst: " + "".join([str(x) for x in ord_lst]))
    
    for i, char in enumerate(filled_input):
        if char == "0":
            random.seed(seed)
            rand_char = random.choice(input_lst)
            char = rand_char
            
            seed_lst = list(seed)
            random.shuffle(seed_lst)
            seed = "".join(seed_lst)
        shuffled_input += chr(ord(char) 
                            + ord_lst[i % original_length] // i 
                            if i % 2 == 0 and i != 0 else 
                            ord_lst[i % original_length] * i)
    debug_print("Shuffled the input: " + shuffled_input)
    
    shuffled_length = len(shuffled_input)
    split_lst, i = [shuffled_input], 1
    param = original_length
    
    while len(split_lst) != shuffled_length:
        debug_print(f"Split_lst: {len(split_lst)}/{shuffled_length}")
        param = ord_lst[i % original_length] = max(1, 
                        ord_lst[i % original_length] // i 
                        if i % 2 == 0 else 
                        ord_lst[i % original_length] * i)
        debug_print("Param: " + str(param))
        
        i2 = -1
        while i2 + 1 < len(split_lst):
            i2 += 1
            element = split_lst[i2]
            debug_print(f"Element: {element}, {len(element)}")
            
            if len(element) <= param:
                continue
            debug_print(f"{element} -> \n1. {element[:param]},\n2. {element[param:]}")
            
            str1, str2 = element[:param], element[param:]
            split_lst[i2] = str1
            split_lst.insert(i2 + 1, str2)
            
        random.seed(param)
        random.shuffle(split_lst)
        i += 1
    return "".join(split_lst)


def hashed_wrapper(input_str: str, length: int, debug: bool = False, sub_debug: bool = False,
                   sub_sub_debug: bool = False, hash_func: Callable[[str, int, bool], str] = lambda x, y, z: None):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    if len(input_str) <= length:
        debug_print("No need to chunk, hashing now ...")
        final_hash = hash_func(input_str, length, sub_debug)
    else:
        debug_print("Input is longer than requested length, chunking needed ...")
        if len(input_str) % length != 0:
            filled_input = input_str.ljust(((len(input_str) // length) + 1) * length, "0") # What if it's exactly e.g. 3*length? Fixed
            input_str = filled_input
            debug_print("Filled input: ", filled_input)
        input_chunks = list(map(''.join, zip(*[iter(input_str)] * length))) # https://stackoverflow.com/questions/22571259/split-a-string-into-n-equal-parts from comment: This method comes straight from the docs for zip().
        debug_print("Input chunks: ", input_chunks)
        hashes_lst = []
        for inp_chunk in input_chunks:
            new_hash = hash_func(inp_chunk, length, sub_sub_debug)
            hashes_lst.append(new_hash)
            debug_print(f"Finished hashing chunk:{repr(new_hash)},Hashing next chunk ...")
        chunks = len(input_chunks)
        avg_length = length // chunks
        lengths = [avg_length] * chunks
        difference = length - sum(lengths)
        debug_print(f"Chunks num {chunks}, \nAverage Length {avg_length}, \nHash lengths {lengths}, \nHash lengths to length difference {difference}")
        for i in range(difference): # Evenly distribute the left over chars
            lengths[i % len(lengths)] += 1 # Could've used chunks instead of len(lengths), but it's more readable like this
        debug_print("New lengths", lengths) # x[y:y+y] x[-y:-2*y:-1]
        final_input = ''.join([x[i:y+i] if i % 2 == 0 else x[y+i:y+y+i] for i, (x, y) in enumerate(zip(hashes_lst, lengths))]) # How to get something unique from every hash and hash the result (should be smaller or equal to length) Fixed
        debug_print(f"Finished hashing all chunks. Hashing combined chunk ({repr(final_input)}) now ...")
        final_hash = hash_func(final_input, length, sub_debug)
        debug_print(final_hash, "<-", final_input, "\n", len(final_hash), "<-", len(final_input))
    return final_hash


def hashed_wrapper_latest(input_str: str, length: int, debug: bool = False, sub_debug: bool = False,
                          sub_sub_debug: bool = False,
                          hash_func: Callable[[str, int, bool], str] = lambda x, y, z: None):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    if len(input_str) <= length:
        debug_print("No need to chunk, hashing now ...")
        final_hash = hash_func(input_str, length, sub_debug)
    else:
        debug_print("Input is longer than requested length, chunking needed ...")
        if len(input_str) % length != 0:
            filled_input = input_str.ljust(((len(input_str) // length) + 1) * length, "0") # What if it's exactly e.g. 3*length? Fixed
            input_str = filled_input
            debug_print("Filled input: ", filled_input)
        input_chunks = list(map(''.join, zip(*[iter(input_str)] * length))) # https://stackoverflow.com/questions/22571259/split-a-string-into-n-equal-parts from comment: This method comes straight from the docs for zip().
        debug_print("Input chunks: ", input_chunks)
        hashes_lst = []
        for inp_chunk in input_chunks:
            new_hash = hash_func(inp_chunk, length, sub_sub_debug)
            hashes_lst.append(new_hash)
            debug_print(f"Finished hashing chunk:{repr(new_hash)},Hashing next chunk ...")
        chunks = len(input_chunks)
        avg_length = length // chunks
        lengths = [avg_length] * chunks
        difference = length - sum(lengths)
        debug_print(f"Chunks num {chunks}, \nAverage Length {avg_length}, \nHash lengths {lengths}, \nHash lengths to length difference {difference}")
        for i in range(difference): # Evenly distribute the left over chars
            lengths[i % len(lengths)] += 1 # Could've used chunks instead of len(lengths), but it's more readable like this
        debug_print("New lengths", lengths) # x[y:y+y] x[-y:-2*y:-1]
        final_input = ''.join([x[i:y+i] if i % 2 == 0 else x[y+i:y+y+i] for i, (x, y) in enumerate(zip(hashes_lst, lengths))]) # How to get something unique from every hash and hash the result (should be smaller or equal to length) Fixed
        debug_print(f"Finished hashing all chunks. Hashing combined chunk ({repr(final_input)}) now ...")
        final_hash = hash_func(final_input, length, sub_debug)
        debug_print(final_hash, "<-", final_input, "\n", len(final_hash), "<-", len(final_input))
    return final_hash


def reducer(input_str: str, ord_range: List[range], jump_size: int, debug: bool = False):
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    max_range, min_range = max(ord_range), min(ord_range)
    output = ""
    for i in input_str:
        ord_i = ord(i)
        debug_print(f"Char {repr(i)} -> Ord {ord_i}")
        if ord_i not in ord_range: # Just send it through both
            while ord_i > max_range:
                ord_i -= jump_size
            i = chr(ord_i) # To make sure it's within chars allowed range
            ord_i = ord(i)
            debug_print(f"New char {repr(i)} -> Ord {ord_i}")
            while ord_i < min_range:
                ord_i += jump_size
            i = chr(ord_i)
        output += i
    return output


def big_reducer(input_str: str, ord_ranges: List[range], jump_size: int, tries: int, debug: bool = False): # It works, but it's very ugly ...
    def debug_print(*args, **kwargs):
        if debug:
            print(*args, **kwargs) # Maybe don't prepare ranges? Iterating over a dict is probably also more expensive than accessing the attributes of a range object
    def prepare_ranges(ranges): # NEVER use max, as it gets .stop-1, because that's how ranges work, but .stop is also more efficient
        return {k: v for k, v in sorted({range: [range.start, range.stop] for range in ranges}.items(), key=lambda r: r[0].start)}
    def within_ranges(ord_val, ranges): # Just prepare lists with all valid characters?
        in_range_lst = []
        for range in ranges.values():
            minimum, maximum = range[0], range[1]
            debug_print(f"Min: {minimum}, Max: {maximum}, Char: {chr(ord_val)}({ord_val})")
            if minimum <= ord_val <= maximum:
                in_range_lst.append(True)
            else:
                in_range_lst.append(False)
        return any(in_range_lst)
    def adjust_to_nearest_range(ord_val, ranges, jump_size, tries):
        def grouped(iterable, n): # https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list # Not used anymore
            "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
            return zip(*[iter(iterable)]*n)
        def nearest_int(target, int1, int2, jump_size, switch=False, differences=[]):
            diff1 = abs(target - int1) if not switch else differences[0]
            diff2 = abs(target - int2) if not switch else differences[1]
            if diff1 < diff2:
                return int1
            elif diff2 < diff1:
                return int2
            else: # If both are equal, just use the one that better fits the jump_size
                if not switch:
                    diff11 = diff1 / jump_size
                    diff21 = diff2 / jump_size
                    return nearest_int(target, int1, int2, jump_size, True, [diff11, diff21])
                else:
                    return int1
        for i in range(tries):
            for i, range1 in enumerate(ranges):
                range_1 = range1
                range_2 = list(ranges.keys())[i+1] if i != len(ranges)-1 else range(range_1.stop, range_1.stop)
                end, start = range_1.stop, range_2.start
                debug_print(end, "<", ord_val, "<", start)
                if end < ord_val < start:
                    target = nearest_int(ord_val, end, start, jump_size)
                    debug_print("Target ", target)
                    if target == end: # This is a little bit less expensive than checking if it's bigger, smaller or equal again
                        while ord_val > end:
                            ord_val -= jump_size
                    else:
                        while ord_val < start:
                            ord_val += jump_size
                elif ord_val < range_1.start and i == 0:
                    while ord_val < range_1.start:
                        ord_val += jump_size
                elif ord_val > range_2.stop and i == len(ranges)-1:
                    while ord_val > range_2.stop:
                        ord_val -= jump_size
            if within_ranges(ord_val, ranges):
                break
            else: debug_print(f"Recalculating char {chr(ord_val)}, {ord_val}")
        return ord_val
    ranges = prepare_ranges(ord_ranges)
    debug_print(ranges)
    output = ""
    for char in input_str:
        ord_i = ord(char)
        debug_print(f"Char {repr(char)} -> Ord {ord_i}")
        if not within_ranges(ord_i, ranges):
            ord_i = adjust_to_nearest_range(ord_i, ranges, jump_size, tries)
            char = chr(ord_i)
            debug_print(f"New char {repr(char)} -> Ord {ord_i}")
        output += char
    return output
    

def num_hasher(input_str: str, length: int, char_range: range = range(32, 126), seed: int = 1):
    """
    This hasher function hashes an input and gives out something
    with around the same length. This can be changed by appending
    random range chars using random.seed result.

    :str input_str:
    :int desired_length:
    :range char_range:
    :int seed:
    :return str:
    """
    # Convert characters to ordinals and concatenate
    ord_concat = ''.join(str(ord(char)) for char in input_str)

    # Convert to integer
    ord_int = int(ord_concat)

    # Apply irreversible operations
    large_prime = 982451653 * seed
    constant_add = 314159265 * seed
    hashed_value = (ord_int * large_prime + constant_add) & 0xFFFFFFFF

    # Convert to string
    hashed_str = str(hashed_value)

    # Splitting the hashed number into segments
    def split_number(h_str):
        parts = []
        i = 0
        while i < len(h_str):
            found = False
            for j in range(len(h_str), i, -1):
                part = int(h_str[i:j])
                if part in char_range:
                    parts.append(chr(part))
                    i = j
                    found = True
                    break
            if not found:  # Fallback for a segment not in the range
                if i < len(h_str) - 1:
                    parts.append(chr(int(h_str[i:i+2]) % 128))  # Use a mod to keep it in ASCII range
                    i += 2
                else:
                    i += 1
        return parts

    result = split_number(hashed_str)

    # Ensure the result matches the desired length
    while len(result) < length:
        random.seed(''.join(result))  # Make it reproducible
        result.append(chr(random.randint(char_range.start, char_range.stop)))  # Append random characters within range

    return ''.join(result[:length])


def local_test():
    try:
        print(hashed_wrapper_latest("Hello World, kitty", 50, hash_func=hashed_latest))

        # Example usage
        input_string = "Hello World, kitty"  # "example"
        desired_length = 50  # 8
        acceptable_chars = range(100, 200)
        print(num_hasher(input_string, desired_length, acceptable_chars))

        inp = "To hash: "
        print(num_hasher(inp, len(inp)))
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
