---
description: 
  Functions and classes are Google -formatted and should be formatted as such. 
  Running of the code performed with virtualenv and pip install -r requirements.txt. The code should be run with Python 3.10 or higher.
  Use logger for logging instead of print statements. The logger should be configured to log to a file and to the console. The log level should be set to INFO by default, but it should be configurable to allow for different log levels (e.g., DEBUG, ERROR).
  Documentation should be included for all functions and classes, following the Google style guide for Python docstrings. This includes a description of the function or class, its parameters, return values, and any exceptions that it may raise.
  You follow the instructions for StakeEngine documentation for the structure of the documentation. You create and update a .txt file with detailed mathematical meaning of every function/criterion, and include instructions on how to run the code and any dependencies that are required. You use the Pirates Treasure Dice Math.docx and Game_Description.md file that is in the folder for initial information.
  The code should be kept as compact as possible, and the documentation should only be updated after the code is working correctly.
  Also create detailed descriptions of your updates as a manual (tutorial) for developers on how to use Stake Engine to create the model of the game and how to use the code to run the model and get the results.
applyTo:
  **/*.py, **/*.json
---
- create virtualenv with python 3.10 or higher\n- install dependencies with pip install -r requirements.txt\n- use logger for logging instead of print statements, configure it to log to a file and to the console, and set the log level to INFO by default
- include documentation for all functions and classes following the Google style guide for Python docstrings
- create and update .txt with detailed mathematical meaning of every function/criterion, and include instructions on how to run the code and any dependencies that are required (use Pirates Treasure Dice Math.docx and Game_Description.md file that is in the folder for initial information and Stake Engine docunmentation for the structure of the documentation)
- run the code with Python 3.10 or higher
- keep code as compact as possible, and only update the documentation after the code is working correctly