from .anpl import ANPL, IOExample
import types
from copy import deepcopy
import functools
from .sandbox import import_module_from_string, timeout
from typing import Optional, Any
import traceback

class IOCollector:

    def __init__(self, fun_name: str, module):
        self.ios = []
        self.fun_name = fun_name
        self.crash = False
        self.exception = None

        # Add deco to the function
        fun = getattr(module, fun_name, None)
        assert fun and isinstance(fun, types.FunctionType), f"{fun_name} is not a function."
        setattr(module, fun_name, self.trace(fun))

    def trace(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            names, values = func.__code__.co_varnames[:func.__code__.co_argcount], args

            inputs = {name: value for name, value in zip(names, values)}
            if kwargs:
                inputs = inputs | kwargs

            frozen_inputs = deepcopy(inputs)
            try:
                output = func(*args, **kwargs)
            except Exception as e:
                self.crash = True
                raise e
                # TODO Should we show user inputs which caused error?
                # self.ios.append(IOExample(inputs, None))
            frozen_output = deepcopy(output)
            self.ios.append(IOExample(frozen_inputs, frozen_output))
            return output
        return wrapper


def anpl_trace(anpl: ANPL, fun_name: str, inputs: dict[str, Any], entry: Optional[str] = None) -> IOCollector:
    # assert len(anpl.get_holes()) == 0, "There are still holes in ANPL"
    module = import_module_from_string(anpl.to_python())
    io = IOCollector(fun_name, module)
    entry_point = getattr(module, entry or anpl.entry, None)
    inputs = deepcopy(inputs) # Important. ANPL Execution should not change the server's env.
    try:
        f = timeout(timeout=1)(entry_point)
        f(**inputs)
        return io
    except Exception as e:
        io.exception = e
        return io

def anpl_check(anpl: ANPL, fun_name: str, show_err: bool=True) -> bool:
    assert len(anpl.funs[fun_name].gloden_ios) > 0
    for io_id, io in enumerate(anpl.funs[fun_name].gloden_ios):
        ioc = anpl_trace(anpl, fun_name, io.inputs, fun_name)
        if show_err and ioc.exception:
            try:
                traceback.print_exception(ioc.exception, limit=-1)
            except Exception:
                print(ioc.exception) 
        if ioc.crash or len(ioc.ios) < 1:
            return False, io_id
        # if len(ioc.ios) > 1:
        #     print("This function should be a recursive function because we have collected many ios. Check")
        real_io = ioc.ios.pop()
        if not (real_io == io):
            print(f"Check: The except IO is {io}")
            print(f"Check: The real IO is {real_io}")
            return False, io_id
    return True, None