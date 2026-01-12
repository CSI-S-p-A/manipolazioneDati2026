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


# Function to load Pandas
def loadPandas():
    import pandas as pd

    return pd


# Function to check if the .txt file is actually a test
# it checks if there is a .spec file in the same folder
def testCheck(test: str) -> bool:
    specPath = test.replace(".txt", ".spec")
    return os.path.exists(specPath)


def decorateSentence(sentence: str, isRed: bool):
    init()
    if isRed:
        print(Fore.RED)
    else:
        print(Fore.YELLOW)
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


# Filtering the data
def filtering(dataVector):
    from scipy import signal

    sos = signal.butter(N=12, Wn=10, fs=100, output="sos")
    return signal.sosfiltfilt(sos, dataVector)


# Processing the ADC6 data
def warningProcess(warningVector, startTestIndex):
    warningOut = warningVector.copy()
    warningOut[:] = 0

    warningThreshold = 1

    # Deriving the warning and chack when the derivative is more than 1
    # this comes from the old processing in Matlab
    dY = warningVector.diff()
    dY[0] = dY[1]
    dY = dY.abs()
    indexFirstWarning = dY.iloc[startTestIndex:][
        dY.iloc[startTestIndex:] > warningThreshold
    ].index.tolist()

    if len(indexFirstWarning) != 0:
        warningOut[indexFirstWarning[0] :] = 5

    return warningOut


# Similar process as the warning but with the yaw velocity
def yawVelocityProcess(yawVelocity, startTestIndex):
    import pandas as pd

    curveTime = pd.Series(filtering(yawVelocity)).copy()
    curveTime[:] = 0
    yawVelocityPositive = pd.Series(yawVelocity).copy().abs()

    warningThreshold = 1.5

    indexFirstWarning = yawVelocityPositive.iloc[startTestIndex:][
        yawVelocityPositive.iloc[startTestIndex:] > warningThreshold
    ].index.tolist()

    if len(indexFirstWarning) != 0:
        curveTime[indexFirstWarning[0] :] = 5

    return curveTime.to_numpy()


# Covert the BR Position to the accellerator position
# the negative values of the brake are the values of the accelerator
def processAcceleratorPosition(dataVector):
    import numpy as np

    dataVector = np.where(dataVector > 0, 0, dataVector)
    dataVector = dataVector / 1000.0
    return np.abs(dataVector)


# Removes the negative value in the BR Position
def processBrakePosition(dataVector):
    import numpy as np

    dataVector = np.where(dataVector < 0, 0, dataVector)
    dataVector = dataVector / 1000.0
    return np.abs(dataVector)


# Managing the final export
# TODO adding the header to the channel when ENCAP defines what it wants
def exportingToChannelFolder(testDirectory, output):
    import numpy as np

    # Creating the Channel folder
    channelFolder = os.path.join(testDirectory, "Channel")
    os.makedirs(channelFolder, exist_ok=True)
    numberOfChannels = len(output)

    count = 1

    with open(os.path.join(channelFolder, "data.chn"), "w") as file:
        file.write("Instrumentation standard    :ISO 6487 :1987\n")
        file.write("Number of channels          :" + str(numberOfChannels) + "\n")

    # Saving to the info in the .chn file
    for channelName, dataVector in output.items():
        currentChannelNumber = str(count).zfill(3)

        with open(os.path.join(channelFolder, "data.chn"), "a") as file:
            file.write(
                "Name of channel "
                + currentChannelNumber
                + "         :"
                + channelName
                + "\n"
            )

        # Saving to every .01 files
        np.savetxt(
            os.path.join(channelFolder, "data." + currentChannelNumber),
            dataVector,
            fmt="%.8f",
        )

        count = count + 1


# Generic function that creates the data from and external time file (like ldw.ini or visual.ini)
def externalTimeProcess(timeValue, table):
    import numpy as np

    outputVector = table["Time"].copy()
    outputVector[:] = 0

    # Finds the closest time value to the one in the file
    idx = np.abs(table["Time"].to_numpy() - timeValue).argmin()

    outputVector[idx:] = 5
    return outputVector.to_numpy()


# Function to create the linear transformation matrix to the VUT
# reference system to the external one
def reference_system_change(yaw_angle, x_position, y_position, x_imu, y_imu):
    import numpy as np

    N = x_position.shape[0]
    T_imu_ext = np.zeros((N, 3, 3))

    angle = np.pi + yaw_angle

    T_imu_ext[:, 0, 0] = np.cos(angle)
    T_imu_ext[:, 0, 1] = -np.sin(angle)
    T_imu_ext[:, 1, 0] = np.sin(angle)
    T_imu_ext[:, 1, 1] = np.cos(angle)

    T_imu_ext[:, 0, 2] = x_position
    T_imu_ext[:, 1, 2] = y_position
    T_imu_ext[:, 2, 2] = 1

    T_vut_imu = np.zeros((N, 3, 3))

    T_vut_imu[:, 0, 0] = 1
    T_vut_imu[:, 1, 1] = 1
    T_vut_imu[:, 2, 2] = 1

    T_vut_imu[:, 0, 2] = -x_imu
    T_vut_imu[:, 1, 2] = -y_imu

    T = T_imu_ext @ T_vut_imu

    return T


#######################################################################################################################################
def reference_system_change_old(yaw_angle, x_position, y_position, x_imu, y_imu):
    import numpy as np

    N = x_position.shape[0]
    T_imupar_ext = np.zeros((N, 3, 3))

    T_imupar_ext[:, 0, 0] = 1
    T_imupar_ext[:, 1, 1] = 1
    T_imupar_ext[:, 2, 2] = 1

    T_imupar_ext[:, 0, 2] = x_position
    T_imupar_ext[:, 1, 2] = y_position

    T_imu_imupar = np.zeros((N, 3, 3))

    T_imu_imupar[:, 0, 0] = np.cos(yaw_angle)
    T_imu_imupar[:, 0, 1] = -np.sin(yaw_angle)
    T_imu_imupar[:, 1, 0] = np.sin(yaw_angle)
    T_imu_imupar[:, 1, 1] = np.cos(yaw_angle)

    T_imu_imupar[:, 2, 2] = 1

    T_vut_imu = np.zeros((N, 3, 3))

    T_vut_imu[:, 0, 0] = 1
    T_vut_imu[:, 1, 1] = 1
    T_vut_imu[:, 2, 2] = 1

    T_vut_imu[:, 0, 2] = -x_imu
    T_vut_imu[:, 1, 2] = -y_imu

    T = T_imupar_ext @ T_imu_imupar @ T_vut_imu

    return T


def calculate_B(x_imu, y_imu, width, yaw_angle):
    import numpy as np

    mod = (x_imu**2 + (width / 2 + y_imu) ** 2) ** 0.5
    theta = np.arccos(x_imu / mod)

    yaw_total = theta + yaw_angle

    print(f"B: {mod}")

    return (mod, yaw_total)


def calculate_A(x_imu, y_imu, overhang, yaw_angle):
    import numpy as np

    mod = ((x_imu + overhang) ** 2.0 + y_imu**2) ** 0.5
    theta = np.arccos((x_imu + overhang) / mod)

    yaw_total = theta + yaw_angle

    print(f"A: {mod}")
    return (mod, yaw_total)


def calculate_C(x_imu, y_imu, width, yaw_angle):
    import numpy as np

    mod = (x_imu**2 + (width / 2 - y_imu) ** 2) ** 0.5
    theta = 2 * np.pi - np.arccos(x_imu / mod)

    yaw_total = theta + yaw_angle
    print(f"C: {mod}")

    return (mod, yaw_total)
