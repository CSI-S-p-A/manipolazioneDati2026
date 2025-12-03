import os

from colorama import Fore, Style, init


def getFolder():
    from tkinter import Tk
    from tkinter.filedialog import askdirectory

    root = Tk()
    root.withdraw()

    sourceFolder = askdirectory(title="Select the folder.")

    if not sourceFolder:
        print("No folder was selected.")
        return None

    return sourceFolder


def loadPandas():
    import pandas as pd

    return pd


def testCheck(test: str) -> bool:
    testFolder = os.path.dirname(test)
    specPath = test.replace(".txt", ".spec")
    return os.path.exists(specPath)


def decorateSentence(sentence: str, isRed: bool):
    init()
    if isRed:
        print(Fore.RED)
    print(
        "---------------------------------------------------------------------------------"
    )
    print(sentence)
    print(
        "---------------------------------------------------------------------------------"
    )
    print(Style.RESET_ALL)
