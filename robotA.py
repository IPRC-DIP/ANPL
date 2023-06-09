from rich.prompt import Confirm, Prompt, IntPrompt
from rich.progress import track
from utils import sys_str, system_info, code_input, value_input, print_anpl, print_IOExamples, select_task, set_openai_key, fun_select, print_text_IOExamples, Logger, print_error
from copy import deepcopy
import time

from anpl.anpl import IOExample, ANPL
from anpl.parser import ANPLParser
from anpl.synthesizer import fun_synthesis, batch_fun_synthesis
from anpl.tracer import anpl_check, anpl_trace


set_openai_key()
task_id, input_grid, output_grid = select_task()
logger = Logger(task_id, "A")

parser = ANPLParser()
anpl = code_input(parser, logger)

def syn_anpl(anpl: ANPL):
    holes = anpl.get_holes()
    for hole in track(holes, description="Synthesizing..."):
        for i in range(5):
            res = fun_synthesis(anpl, hole, temp=i*0.1)
            logger.log("gpt", "syn", res)
            if res:
                newanpl = parser.try_parse(res, from_user=False)
                if newanpl:
                    logger.log("system", "syn", "info: gpt returns valid code")
                    if not hole.startswith("_hole"):
                        if hole in newanpl.funs:
                            newanpl.clean(hole)
                        else:
                            logger.log("system", "syn", "error: do not synthesis the function with specific name")
                            continue
                    else:
                        if newanpl.entry in anpl.funs:
                            if newanpl.entry != hole:
                                logger.log("system", "syn", "error: synthesis _hole with a used name")
                                system_info("[yellow]Warning Generated Function has the same name with some function before. Perhaps you have very similar sentences? It can also be caused by chatgpt generating wrong code")
                            else:
                                logger.log("system", "syn", "error: chatgpt do not give a new function name")
                            continue
                    anpl.fill_fun(hole, newanpl)
                    break
                logger.log("system", "parse_gpt", "error")

    if len(anpl.get_holes()) > 0:
        logger.log("system", "syn", "error: cannot synthesis code")
        raise NotImplementedError("Cannot Synthesis")

def io_input(anpl: ANPL, name: str, logger):
    system_info(f"Please show me an Input-Output example for [italic yellow]{name}[/italic yellow]")
    logger.log("system", "error", "show user function with no code")
    assert anpl.funs[name].code, "No code for function"
    params = anpl.funs[name].get_params()
    ins = {}
    for param in params:
        ins[param] = value_input(param, logger)
    out = value_input("output", logger) 
    anpl.funs[name].gloden_ios.append(IOExample(ins, out))

syn_anpl(anpl)
in_param = anpl.funs[anpl.entry].get_params()
if len(in_param) != 1:
    logger.log("system", "error", "The main function has multi param")
assert len(in_param) == 1, "The main function should have only 1 param."
anpl.funs[anpl.entry].gloden_ios.append(IOExample({in_param[0]: input_grid}, output_grid))
is_correct = anpl_check(anpl, anpl.entry)


while not is_correct:
    system_info("[red]ANPL WRONG[/red] Here is the anpl program.")
    print_anpl(anpl)

    cmd = Prompt.ask(sys_str + "Which command would you like to do? [1] Trace [2] Edit [3] Resynthesis [4] Remove IO [5] Quit", choices=["1", "2", "3", "4", "5"])
    if cmd == "5":
        quit_time = time.time()
        if quit_time - logger.start_time < 30 * 60:
            if Confirm.ask(sys_str + "Less than 30 minutes. Do you really want to exit?"):
                logger.log("user", "quit", "force")
                break
            else:
                continue
        else:
            break

    fun_name = fun_select(anpl, logger, cmd == "1" or cmd == "2")
    if cmd == "1":
        logger.log("user", "trace", f"{fun_name}")
        ioc = anpl_trace(anpl, fun_name, anpl.funs[anpl.entry].gloden_ios[0].inputs)
        if ioc.crash:
            logger.log("system", "trace", f"{fun_name}: crash")
            system_info("[red]ANPL crash in this function.[/red]")
            print_error(ioc.exception)
        elif len(ioc.ios) == 0:
            logger.log("user", "trace", f"{fun_name}: crash before this function")
            system_info("[red]ANPL crash before this function.[/red]")
            print_error(ioc.exception)
        else:
            logger.log("user", "trace", f"{fun_name}: show io to user")
            system_info("[green]Visual IO[/green]")
            print_IOExamples(ioc.ios)
            system_info("[green]Textual IO[/green]")
            print_text_IOExamples(ioc.ios)

    elif cmd == "2":
        logger.log("user", "edit", f"{fun_name}")
        system_info(f"Please input your code for [italic yellow]{fun_name}[/italic yellow]")
        newanpl = code_input(parser, logger)
        if newanpl.entry != fun_name:
            logger.log("system", "edit", f"error: {fun_name} {newanpl.entry} is not match")
            system_info(f"[red]Function name don't match: {fun_name} {newanpl.entry}.[/red]")
            continue
        test_anpl = deepcopy(anpl)
        test_anpl.fill_fun(fun_name, newanpl)
        try:
            syn_anpl(test_anpl)
        except NotImplementedError:
            system_info("[red]Cannot synthesis your code[/red]")
            continue
        anpl = test_anpl

    elif cmd == "3":
        logger.log("user", "resyn", f"{fun_name}")
        io_input(anpl, fun_name, logger)
        system_info("Synthesizing...")
        find_correct_anpl = False
        raw_test_anpl = deepcopy(anpl)
        raw_test_anpl.funs[fun_name].reset_to_hole()
        reses = batch_fun_synthesis(raw_test_anpl, fun_name, 10, 0.8) # The same config as CodeT
        for res in track(reses, description="Checking"):
            if res is None:
                logger.log("gpt", "resyn", "error: gpt return nothing")
                continue
            logger.log("gpt", "resyn", res)
            newanpl = parser.try_parse(res, from_user=False)
            if newanpl is None:
                logger.log("system", "resyn", "error: gpt return wrong python code")
                continue

            if fun_name not in newanpl.funs:
                logger.log("system", "resyn", "error: gpt doesn't synthesis hole")
                continue

            newanpl.clean(fun_name)
            test_anpl = deepcopy(raw_test_anpl)
            test_anpl.fill_fun(fun_name, newanpl)
            if anpl_check(test_anpl, fun_name, show_err=False):
                logger.log("system", "resyn", "info: code pass user's io")
                anpl = test_anpl
                find_correct_anpl = True
                break

        if find_correct_anpl:
            logger.log("system", "resyn", "info: correct")
            system_info("[green]Function Correct[/green].")
        else:
            logger.log("system", "resyn", "info: Resyn failed. Cannot resynthesis correct function")
            system_info("[red]Cannot synthesis correct function.[/red].")
    else:
        logger.log("user", "remove_io", f"{fun_name}")
        ios = anpl.funs[fun_name].gloden_ios
        system_info(f"Here is all IO Examples of {fun_name}.")
        print_IOExamples(ios)
        idx = IntPrompt.ask("Which io would you like to remove? -1 to return")
        logger.log("user", "remove_io", "exit")
        if idx != -1:
            if idx not in range(0, len(ios)):
                logger.log("system", "remove_io", f"error: {fun_name}: {idx}")
                system_info(f"[red]{fun_name} doesn't have the {idx}th IO [/red].")
            else:
                logger.log("system", "remove_io", f"info: {fun_name}: {idx}")
                ios.pop(idx)
        continue

    is_correct = anpl_check(anpl, anpl.entry)
    logger.log("system", "anpl_check", f"{is_correct}")

if is_correct:
    system_info("[green]ANPL CORRECT[/green], and here is the code")
    print_anpl(anpl, for_user=False)
    logger.save(anpl)
else:
    system_info("Good luck next time.")
logger.log("system", "exit", str(is_correct))
