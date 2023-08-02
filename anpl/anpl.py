from dataclasses import dataclass, field, astuple
from typing import Optional, Any
import ast
from copy import deepcopy
from numpy.testing import assert_equal

@dataclass(frozen=True, eq=True)
class IOExample:
    inputs: dict[str, Any]
    output: Any

    def __eq__(self, __value: object) -> bool:
        "compare data structures with numpy array."
        if isinstance(__value, IOExample):
            try:
                assert_equal(astuple(self), astuple(__value))
                return True
            except Exception:
                return False
        else:
            return False

class FunRenamer(ast.NodeTransformer):
    
    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == self.old_name:
            node.func.id = self.new_name
        return self.generic_visit(node)


@dataclass
class Function:
    name: str

    prompt: Optional[str] = None
    code: Optional[ast.FunctionDef] = None
    gloden_ios: list[IOExample] = field(default_factory=list) # Here is a typo

    dependencies: list[str] = field(default_factory=list)

    code_from_user: bool = False
    prompt_from_user: bool = True
    is_recursive: bool = False

    # When changing code, remember to change dependencies and is_recursive

    def reset_to_hole(self):
        self.code = None
        self.dependencies = []
        self.code_from_user = False
        self.is_recursive = False

    def add_dependency(self, name: str):
        if name not in self.dependencies:
            self.dependencies.append(name)

    def get_params(self):
        assert self.code, "Cannot get params for hole"
        return [arg.arg for arg in self.code.args.args]
    
    def rename(self, old_name: str, new_name: str):
        if old_name in self.dependencies:
            self.dependencies[self.dependencies.index(old_name)] = new_name
            renamer = FunRenamer(old_name, new_name)
            renamer.visit(self.code)

    def clean_dep(self, funs_set: set[str]):
        self.dependencies = list(filter(lambda x: x in funs_set, self.dependencies))
    
    @staticmethod
    def merge_logic(s: Any, s_from_user: bool, f: Any, f_from_user: bool) -> Any:
        if f_from_user: return f
        elif s_from_user: return s
        elif s: return s
        else: return f
    
    def merge(self, f: 'Function'):
        # gloden_ios come from user
        if len(f.gloden_ios) > 0:
            self.gloden_ios = f.gloden_ios

        self.prompt = self.merge_logic(self.prompt, self.prompt_from_user, f.prompt, f.prompt_from_user)
        self.prompt_from_user = self.prompt_from_user or f.prompt_from_user
        
        self.code = self.merge_logic(self.code, self.code_from_user, f.code, f.code_from_user)
        self.dependencies = self.merge_logic(self.dependencies, self.code_from_user, f.dependencies, f.code_from_user)
        self.is_recursive = self.merge_logic(self.is_recursive, self.code_from_user, f.is_recursive, f.code_from_user)
        self.code_from_user = self.code_from_user or f.code_from_user
        

class ANPL:

    ENV = ast.parse('''
from typing import *
''')

    def __init__(self, funs: dict[str, Function], entry: str):
        self.funs = funs
        self.entry = entry

    def find_dependencies(self, name: str) -> list[str]:
        funs_list, queue = [], [name]
        while len(queue) != 0:
            fun = queue.pop(0)
            if (fun in self.funs) and (fun not in funs_list):
                funs_list.append(fun)
                queue.extend(name for name in self.funs[fun].dependencies)
        return funs_list

    def rename(self, old_name: str, new_name: str):
        for fun in self.funs.values():
            fun.rename(old_name, new_name)
        f = self.funs.pop(old_name)
        f.name = new_name
        self.funs[new_name] = f

    def fill_fun(self, name: str, anpl: 'ANPL'):
        # assert not (len(self.get_holes()) > 0 and len(anpl.get_holes()) > 0), "Both ANPL have holes"
        self.funs[name].reset_to_hole()
        if anpl.entry != name:
            self.rename(name, anpl.entry)
            name = anpl.entry
        for newname, newfun in anpl.funs.items():
            if newname not in self.funs:
                self.funs[newname] = newfun
            else:
                self.funs[newname].merge(newfun)
        self.clean(self.entry)
    
    def clean(self, name: str):
        assert name in self.funs.keys(), "Cannot find function"
        remained_funs = [fun_name for fun_name in self.find_dependencies(name)]
        removed_funs = [fun_name for fun_name in self.funs.keys() if fun_name not in remained_funs]
        for fun_name in removed_funs:
            self.funs.pop(fun_name, None)
        self.entry = name

    def get_holes(self) -> list[str]:
        return [f.name for f in self.funs.values() if not f.code]
    
    def user_known_funs(self) -> list[str]:
        return [f.name for f in self.funs.values()]

    def to_python(self, name: Optional[str] = None, for_user=False) -> str:
        funs_name = reversed(self.find_dependencies(name or self.entry))
        funs = map(lambda x: self.funs[x], funs_name)
        selected_funs = filter(lambda f: f.code and (f.code_from_user or not for_user), funs)
        codes = deepcopy(ANPL.ENV)
        codes.body.extend(f.code for f in selected_funs)
        # ast.fix_missing_locations(codes) Maybe Useful?
        return ast.unparse(codes)
    