from anpl.synthesizer import raw_query, msg
from utils import (
    sys_str,
    system_info,
    multiline_input,
    select_task,
    set_openai_key,
    rich_dumps,
    Logger,
    print_error,
)
from rich.prompt import IntPrompt, Confirm, Prompt
import rich
from anpl.sandbox import import_module_from_string, timeout
import time
from copy import deepcopy
import json
from anpl.parser import ANPLParser
import ast, sys
from anpl.anpl import IOExample, ANPL
from anpl.tracer import anpl_check
from utils import code_input
import argparse

ANPL.ENV = ast.parse(
    """import sys
import time
import itertools
from itertools import accumulate, product, permutations, combinations
import collections
from collections import Counter, OrderedDict, deque, defaultdict, ChainMap
from functools import lru_cache
import math
from math import sqrt, sin, cos, tan, ceil, fabs, floor, gcd, exp, log, log2
import fractions
from typing import List, Tuple
import numpy as np
import random
import heapq"""
)

task_id = IntPrompt.ask("Which APPS task would you like to try?")
task = None
with open("cf_task/data.jsonl", "r", encoding="utf-8") as f:
    tasks = [json.loads(line) for line in f.readlines()]
    task_lst = list(filter(lambda t: t["id"] == task_id, tasks))
    if len(task_lst) != 1:
        print("Invalid task id")
        exit(0)
    else:
        task = task_lst[0]

io = json.loads(task["input_output"])
input_examples, output_examples = io["inputs"], io["outputs"]
print("---INPUT---")
print({"inp": input_examples[0]})
print("---OUTPUT---")
print({"out": output_examples[0]})
ans = False
while not ans:
    ans = Confirm.ask("Would you like to start?")
logger = Logger(task_id, "APPSC")


system_info(
    "Code will be executed from main function. The signature of main function should be `def main(inp):`"
)

def get_code():
    while True:
        path = Prompt.ask("Please enter your path of code")
        try:
            with open(path, "r") as f:
                original_code = f.read()
            break
        except Exception as e:
            print(e)
            print("Cannot read your code")
    return original_code

is_correct = False
while not is_correct:
    original_code = get_code()
    parser = ANPLParser()
    anpl = parser.try_parse(original_code)
    if anpl is None:
        logger.log("system", "parser", "user enter wrong code")
        system_info("[red]Your code is not correct. Please try again.[/red]")
        break

    logger.log("user", "check", anpl.to_python(for_user=False))
    in_param = anpl.funs[anpl.entry].get_params()
    if len(in_param) != 1:
        logger.log("system", "error", "The main function has multi param")
        print("The main function should have only 1 param.")
    for inp, out in zip(input_examples, output_examples):
        anpl.funs[anpl.entry].gloden_ios.append(IOExample({in_param[0]: inp}, out))
    is_correct, io_id = anpl_check(anpl, anpl.entry)
    if is_correct:
        logger.log("system", "check", f"correct")
        system_info("[green]Code CORRECT[/green]")
        logger.save(anpl.to_python(for_user=False))
    else:
        logger.log("system", "check", f"wrong")
        system_info("[red]Code WRONG[/red]")


logger.log("system", "exit", str(is_correct))
