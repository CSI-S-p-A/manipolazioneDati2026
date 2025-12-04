import os

from colorama import Fore, Style, init

from test_checks import TestType


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


def TTCProcess(TTCVector, timeVector):
    if (TTCVector == 0).all():
        raise ValueError(
            "The TTC for the current test was empty and could be processed."
        )

        newTime = None
        startTimeIndex = None
        return (newTime, startTimeIndex)

    # Lazy import numpy only when needed
    import numpy as np

    index = 0

    # The loop tries to fill holes in the TTC columns where the TTC is 0
    while index < len(TTCVector) or not index:
        if TTCVector[0] == 0:
            index = TTCVector[TTCVector > 0].index.tolist()[0]
            TTCVector[0:index] = TTCVector[index]
            index = 0

        index = TTCVector[TTCVector == 0].index.tolist()

        if len(index) == 0:
            break
        else:
            index = index[0]

        yStart = (TTCVector[index - 1], index - 1)
        index = TTCVector[index:][TTCVector > 0].index.tolist()

        if len(index) == 0:
            startTestIndex = 0
            break
        else:
            index = index[0]

        yEnd = (TTCVector[index], index)
        xEq = np.arange(0, yEnd[1] - yStart[1])
        m = (yEnd[0] - yStart[0]) / (yEnd[1] - yStart[1])
        TTCEq = m * xEq + yStart[0]
        TTCVector[yStart[1] : yEnd[1]] = TTCEq

    # Shifts the Time frame to start at TTC 4
    startTestIndex = TTCVector[TTCVector < 4].index.tolist()

    if len(startTestIndex) == 0:
        startTestIndex = 0
    else:
        startTestIndex = startTestIndex[0]

    newTime = timeVector[startTestIndex:] - 4 - timeVector[startTestIndex]

    return (newTime, startTestIndex)


def filtering(dataVector):
    from scipy import signal

    sos = signal.butter(N=12, Wn=10, fs=100, output="sos")
    return signal.sosfiltfilt(sos, dataVector)


def warningProcess(warningVector, startTestIndex):
    warningOut = warningVector.copy()
    warningOut[:] = 0

    warningThreshold = 1

    dY = warningVector.diff()
    dY[0] = dY[1]
    dY = dY.abs()
    indexFirstWarning = dY.iloc[startTestIndex:][
        dY.iloc[startTestIndex:] > warningThreshold
    ].index.tolist()

    if len(indexFirstWarning) != 0:
        warningOut[indexFirstWarning[0] :] = 5

    return warningOut


def processAcceleratorPosition(dataVector):
    for item in dataVector:
        if item > 0:
            item = 0

    return dataVector.abs()


def processBrakePosition(dataVector):
    for item in dataVector:
        if item < 0:
            item = 0

    return dataVector.abs()
