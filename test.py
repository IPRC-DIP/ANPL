from anpl.parser import ANPLParser

prev_anpl = r"""
def count_score(str):
  "For each 'h' in the given string str, for each 's' to its left side, add 1 to the score."

def main(inp):
  strs = inp.split('\n')[1:]
  out = `sort the strs according to the following rule: for each pair a and b, place 'a' earlier if the score of 'a + b' is greater than the score of 'b + a'.`(strs, count_score)
  res = count_score(''.join(out))
  return f'{res}\n'
"""

new_anpl = r"""
from typing import *
import functools

def sort_strings(strs: List[str], score_func: Callable[[str], int]) -> List[str]:
    "Sorts the strings according to the following rule: for each pair a and b, place 'a' earlier if the score of 'a + b' is greater than the score of 'b + a'."

    def compare_strings(a: str, b: str) -> int:
        score_ab = score_func(a + b)
        score_ba = score_func(b + a)
        if score_ab > score_ba:
            return -1
        elif score_ab < score_ba:
            return 1
        else:
            return 0
    return sorted(strs, key=functools.cmp_to_key(compare_strings))

def main(inp):
    strs = inp.split('\n')[1:]
    out = sort_strings(strs, count_score)
    res = count_score(''.join(out))
    return f'{res}\n'
"""

def clean_gpt(prev_anpl, new_anpl):
    new_fun_names = set(new_anpl.funs.keys() - prev_anpl.funs.keys())
    subfuns = set()
    for name in new_fun_names:
        if name in new_anpl.funs:
            for n in new_anpl.funs[name].dependencies:
                subfuns.add(n)
    entries = new_fun_names - subfuns
    print(entries)
    if len(entries) == 1:
        new_anpl.clean(entries.pop())
        return True
    else:
        return False

a = ANPLParser()
t = a.parse(prev_anpl)
t2 = a.parse(new_anpl, False)
print(clean_gpt(t, t2))