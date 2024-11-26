class TypeMagazineError(Exception):
    pass

class LineNameMagazineError(Exception):
    pass

def is_number(input_str):
    try:
        # float(input_str)  # This will successfully convert both integers and floats
        int(input_str)
        return True
    except ValueError:
        return False