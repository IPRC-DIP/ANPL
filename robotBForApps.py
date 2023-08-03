from anpl.synthesizer import raw_query, msg
from utils import sys_str, system_info, multiline_input, select_task, set_openai_key, rich_dumps, Logger, print_error
from rich.prompt import IntPrompt, Confirm, Prompt
import rich
from anpl.sandbox import import_module_from_string, timeout
import time
from copy import deepcopy
import webbrowser
import json
from anpl.parser import ANPLParser
from anpl.anpl import IOExample
from anpl.tracer import anpl_check
from utils import code_input

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
task_id = IntPrompt.ask("Which APPS task would you like to try?")
task = None
with open("cf_task/data.jsonl", "r", encoding='utf-8') as f:
    tasks = [json.loads(line) for line in f.readlines()]
    task_lst = list(filter(lambda t: t['id'] == task_id, tasks))
    if len(task_lst) != 1:
        print("Invalid task id")
        exit(0)
    else:
        task = task_lst[0]

url = task["url"]
webbrowser.open(url)
io = json.loads(task["input_output"])
input_examples, output_examples = io["inputs"], io["outputs"]
print("---INPUT---")
print({'inp': input_examples[0]})
print("---OUTPUT---")
print({'out': output_examples[0]})
ans = False
while not ans:
    ans = Confirm.ask("Would you like to start?")
logger = Logger(task_id, "APPSB")

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
            res = raw_query(history, model="gpt-3.5-turbo-0301", max_tokens=2048, n=1, temperature=0)
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
        system_info("Code will be executed from main function. The signature of main function should be `def main(inp):`")
        parser = ANPLParser()
        anpl = code_input(parser, logger)
        logger.log("user", "check", anpl.to_python(for_user=False))
        in_param = anpl.funs[anpl.entry].get_params()
        if len(in_param) != 1:
          logger.log("system", "error", "The main function has multi param")
          print("The main function should have only 1 param.")
          continue
        for inp, out in zip(input_examples, output_examples):
          anpl.funs[anpl.entry].gloden_ios.append(IOExample({in_param[0]: inp}, out))
        is_correct, io_id = anpl_check(anpl, anpl.entry)
        if is_correct:
            logger.log("system", "check", f"correct")
            system_info("[green]Code CORRECT[/green]")
            logger.save(anpl.to_python(for_user=False))
            is_correct = True
        else:
            logger.log("system", "check", f"wrong")
            system_info("[red]Code WRONG[/red]")

    else:
        quit_time = time.time()
        if quit_time - logger.start_time < 30 * 60:
            if Confirm.ask(sys_str + "Less than 30 minutes. Do you really want to exit?"):
                logger.log("user", "quit", "force")
                break
        else:
            break

logger.log("system", "exit", str(is_correct))
