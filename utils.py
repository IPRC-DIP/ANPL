from anpl.anpl import IOExample
from rich import print
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import numpy as np
import json
from rich.prompt import Prompt, IntPrompt
from numpy import array
import openai
import time
import os
import pickle
import prompt_toolkit
import traceback
np.set_printoptions(threshold=np.inf)

colors = ["#000000", "#0000FF", "#FF0000", "#008000", "#FFFF00",
          "#808080", "#FFC0CB", "#FFA500", "#008080", "#800000"]

def array_to_str(matrix):
    try:
        text = Text()
        if matrix.ndim == 2:
            for row in list(matrix):
                for pixel in row:
                    text.append("⬛", style=colors[pixel])
                text.append("\n")
        elif matrix.ndim == 1:
            for pixel in list(matrix):
                text.append("⬛", style=colors[pixel])
        else:
            raise NotImplementedError
        return text
    except Exception:
        return Text(str(matrix))

def rich_dumps(obj):
    def _dump_recursive(obj):
        text = Text()
        if isinstance(obj, np.ndarray):
            return array_to_str(obj)
        elif isinstance(obj, (list, tuple)):
            text.append("[")
            for x in obj:
                text.append(_dump_recursive(x))
                text.append(" ")
            text.append("]")
            return text
        elif isinstance(obj, dict):
            text.append("{")
            for k, v in obj.items():
                text.append(str(k) + ": ")
                text.append(_dump_recursive(v))
                text.append("\n")
            text.append("}")
            return text
        else:
            return Text(str(obj), style="blue")

    dumped_obj = _dump_recursive(obj)
    return dumped_obj


def multiline_input():
    system_info("Press [Esc] followed by [Enter] to accept input.")
    buffer = prompt_toolkit.prompt(">", multiline=True, wrap_lines=False, mouse_support=True)
    return buffer

sys_str = "[bold red]SYSTEM: [/bold red]"
def system_info(text):
    print(sys_str + text)

def print_anpl(anpl, for_user=False):
    print(Syntax(anpl.to_python(for_user=for_user), "python"))

def print_text_IOExamples(ios: list[IOExample]):
    if len(ios) > 5:
        system_info("Too many IOs. Only show the first 5 IO")
        ios = ios[:5]
    for i, io in enumerate(ios):
        print(f"The {i}th IO exmaples is")
        for k in io.inputs.keys():
            input_str = " ".join(io.inputs[k].__repr__().split())
            print(f"{k}: {input_str}")
        output_str = " ".join(io.output.__repr__().split())
        print(f"output: {output_str}")        

def print_IOExamples(ios: list[IOExample]):
    # TODO assume len of output is all the same
    if len(ios) > 5:
        system_info("Too many IOs. Only show the first 5 IO")
        ios = ios[:5]
    table = Table(title="Inputs & Output")
    assert len(ios) > 0, "don't have IO examples"
    fio = ios[0]
    table.add_column("IOExample id")
    for k in fio.inputs.keys():
        table.add_column(k)
    table.add_column("Output")
    
    for i, io in enumerate(ios):
        lst = [str(i)]
        lst.extend([rich_dumps(io.inputs[k]) for k in fio.inputs.keys()])
        lst.append(rich_dumps(io.output))
        table.add_row(*lst)
    print(table)

def code_input(parser, logger):
    anpl = None
    system_info("Please enter your anpl code.")

    while anpl is None:
        user_input = multiline_input()
        logger.log("user", "enter code", user_input)
        anpl = parser.try_parse(user_input)
        if anpl is None:
            logger.log("system", "parser", "user enter wrong code")
            system_info("[red]Your code is not correct. Please try again.[/red]")
    logger.log("system", "parser", "user enter correct code")
    return anpl

def value_input(param, logger):
    while True:
        try:
            system_info(f"Please enter the value of [italic purple]{param}[/italic purple].")
            user_input = input()
            logger.log("user", "enter_io", f"{param}: {user_input}")
            return eval(user_input)
        except Exception as e:
            logger.log("system", "check_user_io", "invalid python expression")
            system_info("[red]Wrong. Please try again.[/red]")

def fun_select(anpl, logger, with_main=False):
    funs = [fname for fname in anpl.user_known_funs() if with_main or (fname != anpl.entry)]

    table = Table(title="Functions")
    table.add_column("[green]Function name[/green]")
    table.add_column("has [blue]Code[/blue] or has [yellow]Prompt[/yellow]")
    table.add_column("The number of IO Examples")

    for fun_name in funs:
        fun = anpl.funs[fun_name]
        table.add_row(fun_name, "[blue]Code[/blue]" if fun.code_from_user else "[yellow]Prompt[/yellow]", str(len(fun.gloden_ios)))
    print(table)
    fun_name = Prompt.ask(sys_str + "Which function do you want to select?", choices=funs)

    logger.log("user", "select function", fun_name)
    return fun_name

def set_openai_key():
    openai.api_key_path = "./key.txt"


class Logger:

    def __init__(self, task_id, system_name):
        timestr = time.strftime("%m%d%H%M%S")
        self.task_id = task_id
        self.system_name = system_name
        self.start_time = time.time()
        self.folder_path = f"./log/task{task_id}_{system_name}"
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
        self.file_name = f"{self.folder_path}/task_{system_name}_{task_id}_{timestr}.log"

    def log(self, role, action, content):
        s = {"role": role, "action": action, "content": content, "time": time.time()}
        with open(self.file_name, "a") as f:
            f.write(json.dumps(s))
            f.write("\n")

    def save(self, object):
        timestr = time.strftime("%m%d%H%M%S")
        if self.system_name == "A":
            with open(f"{self.folder_path}/task{self.task_id}_{timestr}.pkl", "wb") as f:
                pickle.dump(object, f)
        elif self.system_name == "B":
            with open(f"{self.folder_path}/btask{self.task_id}_{timestr}.py", "w") as f:
                f.write(object)
        else:
             with open(f"{self.folder_path}/task{self.task_id}_{timestr}.pkl", "wb") as f:
                pickle.dump(object, f)
            # raise NotImplementedError("Unknown System")


def select_task():
    task_id = IntPrompt.ask(sys_str + "Which problem do you want to solve?")
    assert task_id >= 0 and task_id < 400, "Please input a valid task id"
    
    with open(f"./data/{task_id}.json", "r") as f:
        data = json.load(f)
        input_grid = np.array(data["input"])
        output_grid = np.array(data["output"])

    return task_id, input_grid, output_grid

def print_error(e):
    try:
        traceback.print_exception(e, limit=-1)
    except Exception:
        print(e)