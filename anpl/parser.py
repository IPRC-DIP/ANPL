from .anpl import ANPL, Function
from typing import Tuple, Optional
import re
import ast
from .sandbox import import_module_from_string


class FunctionDef(ast.NodeVisitor):

    @staticmethod
    def is_hole(node: ast.FunctionDef):
        """
        functions with nothing but a signature can not be parsed
        functions that only have docstring is a hole
        see cpython ast.py get_docstring
        """
        if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
            s = node.body[0].value
            return isinstance(s, ast.Str) or (isinstance(s, ast.Constant) and isinstance(s.value, str))
        return False

    def __init__(self, undefined_funs: dict[str, Function], from_user: bool):
        self.defined_funs: dict[str, Function] = {}
        self.undefined_funs = undefined_funs
        self.from_user = from_user
        self.current_caller = None

    def visit_FunctionDef(self, node):
        if self.is_hole(node):
            self.defined_funs[node.name] = Function(node.name, ast.get_docstring(node), code_from_user=False, prompt_from_user=self.from_user)
        else:
            self.current_caller = Function(node.name, ast.get_docstring(node), node, code_from_user=self.from_user, prompt_from_user=self.from_user)
            self.defined_funs[node.name] = self.current_caller
            self.generic_visit(node)
        
    def visit_Call(self, node):
        # If there is no current_caller, it should be top-level expression to compute some constants.
        if self.current_caller and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == self.current_caller.name:
                self.current_caller.is_recursive = True
            else:
                self.current_caller.add_dependency(func_name)
        self.generic_visit(node)

class ANPLParser:

    def __init__(self):
        self.hole_id = 0
        self.inline_fun_def_pattern = re.compile(r'(?<=`).+?(?=`)')

    def extract_inline_function_def(self, source_code: str) -> Tuple[str, dict[str, Function]]:
        inline_funs = list(dict.fromkeys(re.findall(self.inline_fun_def_pattern, source_code)))
        funs = {}
        for doc in inline_funs:
            name = f"_hole{self.hole_id}"
            self.hole_id += 1
            funs[name] = Function(name, doc)
            source_code = source_code.replace(f"`{doc}`", name)
        return source_code, funs
    
    def parse(self, source_code: str, from_user: bool=True) -> ANPL:
        source_code, undefined_funs = self.extract_inline_function_def(source_code)

        module_node = ast.parse(source_code)
        visitor = FunctionDef(undefined_funs, from_user)
        visitor.visit(module_node)
        defined_funs = visitor.defined_funs
        funs = undefined_funs | defined_funs

        subfuns = {name for fun in funs.values() for name in fun.dependencies}
        entries = set(defined_funs.keys()) - subfuns
        assert len(entries) == 1, "The number of entry is not 1"

        anpl = ANPL(funs, entries.pop())
        # another check
        import_module_from_string(anpl.to_python())
        return anpl
    
    def try_parse(self, source_code, from_user=True) -> Optional[ANPL]:
        old_hole_id = self.hole_id
        try:
            return self.parse(source_code, from_user)
        except Exception as e:
            print(e)
            self.hole_id = old_hole_id
            return None
