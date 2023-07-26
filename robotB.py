from anpl.synthesizer import raw_query, msg
from utils import sys_str, system_info, multiline_input, select_task, set_openai_key, rich_dumps, Logger, print_error
from rich.prompt import IntPrompt, Confirm, Prompt
import rich
from anpl.sandbox import import_module_from_string, timeout
import numpy as np
import time
from copy import deepcopy

history = []
def print_msg(message):
    role, text = message["role"], message["content"]    
    rich.print(f"[blue]{role}[/blue]:")
    print(text)

def print_history():
    for i, message in enumerate(history):    
        print(f"Message{i} ", end="")
        print_msg(message)

set_openai_key()
task_id, inp, real_out = select_task()
logger = Logger(task_id, "B")

is_correct = False
while not is_correct:
    cmd = Prompt.ask(sys_str + "Which command would you like to do? [1] Chat [2] Remove history [3] Check Code [4] Quit", choices=["1", "2", "3", "4"])
    
    if cmd == "1":
        system_info("Please input your description or IO examples")
        user_input = multiline_input()
        new_message = msg("user", user_input)
        history.append(new_message)

        logger.log("user", "chat", new_message)
        system_info("Waiting for ChatGPT...")
        try:
            res = raw_query(history, model="gpt-3.5-turbo", max_tokens=1024, n=1, temperature=0)
        except Exception as e:
            system_info("[red]ChatGPT Error[/red]")
            logger.log("gpt", "error", str(e))
            print(e)
            continue

        res = res["choices"][0]["message"]
        logger.log("gpt", "responce", res)

        history.append(res)
        print_msg(res)

    elif cmd == "2":
        if len(history) > 0:
            print_history()
            msg_idx = IntPrompt.ask(sys_str + "Remove all messages after the i-th message (including message i)")
            if msg_idx < 0 or msg_idx > len(history):
                logger.log("user", "remove", "invalid idx")
                system_info("[red]Please input a valid message id[/red]")
            else:
                logger.log("user", "remove", str(msg_idx))
                history = history[:msg_idx]
                system_info("[green]DONE[/green]")
        else:
            logger.log("user", "remove", "no history")
            system_info("[red]No history[/red]")

    elif cmd == "3":
        system_info("Code will be executed from main function. The signature of main function should be `def main(input_grid):`")
        system_info("Please enter your code")
        code = multiline_input()
        logger.log("user", "check", code)
        try:
            m = import_module_from_string(code)
            inp_t = deepcopy(inp)
            f = timeout(timeout=1)(m.main)
            out = f(inp_t)
        except Exception as e:
            logger.log("system", "check", f"crash: {e}")
            system_info("[red]Crash[/red]")
            print_error(e)
            continue
        if np.array_equal(out, real_out):
            logger.log("system", "check", f"correct")
            system_info("[green]Code CORRECT[/green]")
            logger.save(code)
            is_correct = True
        else:
            logger.log("system", "check", f"wrong")
            system_info("[red]Code WRONG[/red]")
            rich.print("The output is")
            rich.print("[green]Visual Output[/green]")
            rich.print(rich_dumps(out))
            rich.print("[green]Textual Output[/green]")
            print(" ".join(out.__repr__().split()))
    else:
        quit_time = time.time()
        if quit_time - logger.start_time < 30 * 60:
            if Confirm.ask(sys_str + "Less than 30 minutes. Do you really want to exit?"):
                logger.log("user", "quit", "force")
                break
        else:
            break

logger.log("system", "exit", str(is_correct))
