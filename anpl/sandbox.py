import importlib
import functools
from threading import Thread

def import_module_from_string(source: str):
    spec = importlib.util.spec_from_loader("arc", loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(source, module.__dict__)
    return module

def timeout(timeout):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (
                func.__name__, timeout))]

            def f():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception as e:
                    res[0] = e
            t = Thread(target=f, daemon=True)
            try:
                t.start()
                t.join(timeout)
            except Exception as e:
                res[0] = e
            ret = res[0]
            if isinstance(ret, BaseException):
                raise ret
            return ret
        return wrapper
    return deco
