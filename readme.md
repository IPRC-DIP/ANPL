# ANPL

Source code for [ANPL: Compiling Natural Programs with Interactive Decomposition](https://arxiv.org/abs/2305.18498)

## Installation

This project requires Python version >= 3.11.
Execute the following command to install the environment.
`pip install -r requirements.txt`
Prior to initiating the system, it is essential to input your OpenAI key into the "key.txt" file.

## ANPL Syntax

An ANPL program consists of a python-like sketch, and natural language holes.

### Hole

A hole implements a function module with a natural language description, which will be fleshed out by LLMs during the compiling process.
Each hole specified with a natural language description quoted by quotation marks `` or """.
When called, holes should be organized by specifying its input-output variables, serving as the interconnections.
To define a hole, users can either
1) define a hole as a sub-function with the function name, parameters, and descriptions, and then call the function with its function name and input-output variables, or
2) just define and call it with descriptions and input-output variables inline.

### Sketch

A sketch is the control/data flow connecting different holes, specified with a programmatic language. 
Users constitute the sketch by assigning names to variables and using them as hole parameters in a data flow graph.
Besides, users can write complex control flows with programmatic keywords (e.g., for, while, if) similar to that in Python to get more intricate ANPL programs.

```python
def main(input_grid: np.ndarray) -> np.ndarray:
    """
    In the input, you should see a 6x3 grid with black and blue pixels.
    There is a pattern that repeats itself from top to bottom.
    """
    repeating_unit = `find the smallest repeating unit`(input_grid)
    output_grid = `copy the repeating unit to fill the grid from top to down`(repeating_unit)
    output_grid = `replace blue pixels with red`(output_grid)
    return output_grid
```

## System A:  ANPL

Run `python robotA.py` to start the System A.
The log files generated will be stored in the "log" directory.

SystemA provides a suite of four primary command functionalities:

1. Trace IO: This command allows the user to inspect the input and output of a given function. It visually represents the result and also provides a textual representation of the function's IO.
2. Edit: This command involves using an ANPL program to implement changes to a specified 'hole'. Once this command is executed, SystemA initiates a search for these holes and proceeds with the implementations. There are two possible situations to consider here:
    - If only a docstring is provided, it serves as a natural language alteration for the hole.
    - If a complete ANPL function, including a function body, is supplied, it functions as a decomposer, simplifying a more complex hole into several simpler ones.
3. Resynthesis: This command enables the user to input a set of IO as a constraint for a particular function. SystemA then re-generates the function's implementation until it meets the provided IO constraint. The IO provided by the user is stored, and the newly generated function that aligns with all the user-provided IO is deemed as correct.
4. Remove IO: This command allows users to delete the IO of a designated function.