import os
import shutil
from io import StringIO
from typing import List

import functions
import plotting
import test_checks
from test_checks import TestType


def main():
    sourceFolder = functions.getFolder()
    if not sourceFolder:
        return

    # Copying the folder content and placing the "_manipulated" suffix
    parentFolder = os.path.dirname(sourceFolder)
    folderName = os.path.basename(sourceFolder)
    manipulatedFolderName = folderName + "_manipulated"
    print("Copying files...")
    manipulatedFolder = os.path.join(parentFolder, manipulatedFolderName)
    shutil.copytree(sourceFolder, manipulatedFolder, dirs_exist_ok=True)
    print("All files have been copied.\n")

    # os.walk scans recursevely all the files and folders in the directory
    # This first cycle removes the CurrentTestSpec.txt
    for root, dirs, files in os.walk(manipulatedFolder, topdown=False):
        for file in files:
            if file.endswith(".txt") and "Current" in file:
                fullPath = os.path.join(root, file)
                os.remove(fullPath)

    # This second cycle checks all the files and appends to a list all
    # the .txt files
    txtFiles: list[str] = []
    for root, dirs, files in os.walk(manipulatedFolder):
        for file in files:
            if file.endswith(".txt"):
                fullPath = os.path.join(root, file)
                txtFiles.append(fullPath)

    nTests = len(txtFiles)

    # Initialization of the list of all the tests that were not processed correctly with also
    # the error that made them not go through
    failedFiles: list[tuple[str, Exception]] = []
    currentTestCount = 0

    # This loads the Pandas library, i've placed it here because the startup time on
    # the remote desktop was too high so I've distrubuted the loading time of the app
    pd = functions.loadPandas()
    print("Found", nTests, "test files to process.")

    # Start of the main loop that process every test
    for test in txtFiles:
        currentTestCount += 1
        folderTest = os.path.dirname(test)
        relativePath = test.replace(manipulatedFolder, "")

        # If the .txt is not a test, skip to the next .txt file
        if not functions.testCheck(test):
            print(relativePath + " was not a test.")
            os.remove(test)
            continue

        # Try/Except, if there is an error inside the "try:"
        # the program doesn't crash but it goes to the "except:" block below
        try:
            # Opening the content of the file in "fileContent"
            with open(test, "r") as file:
                fileContent = file.readlines()

            # Parsing the header of the file, getting the number of data points
            # from the second line of the file that is like: "Points=XXXX"
            descriptionLines = fileContent[:2]
            numberDataRows = int(descriptionLines[1].split("=")[1].strip())

            totalLines = len(fileContent)
            unitsOfMeasure = fileContent[3]

            headerLines = descriptionLines
            headerLines.append(unitsOfMeasure)

            # The file contains the header and also some junk at the end,
            # this vector lists the lines that need to be skipped and passes it as "skiprows"
            # to the "read_csv" function of Pandas (pd)
            rowsSkipped = [0, 1, 3] + list(range(4 + numberDataRows, totalLines))

            data = StringIO("".join(fileContent))

            # Loading the data in to a table
            table = pd.read_csv(
                data,
                skiprows=rowsSkipped,
                header=0,
                encoding="cp1252",
                delimiter="\t",
                dtype=float,
            )

            # This is needed to rename the "ADC6" if SOMEONE forget and left it as
            # BR Analogue or whatever
            # This finds "ADC5" and renames the column next to it, if it doesnt find ADC5
            # because that is also with another name, i'm sorry this was the best i could do
            index_ADC5 = table.columns.get_loc("ADC5")
            if type(index_ADC5) is int:
                table.rename(
                    columns={table.columns[index_ADC5 + 1]: "ADC6"}, inplace=True
                )

            # Checks the type of the test
            testType = []
            testType = test_checks.testCheck(test)

            dataTime = table["Time"].copy()

            # This finds the "startTestIndex" that for AEB tests where TTC is roughtly 4
            # I couldn't find a similar criteria for LSS tests so for now is just = 500
            if test_checks.TestType.LSS not in testType:
                dataTTC = table["Time to collision (longitudinal)"]
                [newTime, startTestIndex] = functions.TTCProcess(dataTTC, dataTime)
            else:
                # TODO here the startTestIndex and new time should be calculated for
                # LSS from different sources, like the steering and the current position on the path
                startTestIndex = 500

            # Initializing the python dictionary with the data to be export
            exportData = {}

            # As seen in the CA004 the three main informations that needs to be encoded in the
            # chanell files are relative to the Time, the VUT (like speed/position/state of the pedals)
            # and Target.
            timeProcess(table, exportData, startTestIndex, testType, test)
            VUTProcess(table, exportData, testType, folderTest)
            targetProcess(table, exportData, testType)

            # Just the animation plot for debug sake
            if currentTestCount == 6:
                #                plotting.animation_3_points(
                # plotting.animate_car_frame(
                plotting.animation_car_points(
                    exportData["10VEHC000000DSXP"],
                    exportData["10VEHC000000DSYP"],
                    exportData["11WHEL000000DSXP"],
                    exportData["11WHEL000000DSYP"],
                    exportData["13WHEL000000DSXP"],
                    exportData["13WHEL000000DSYP"],
                    table["X position"].to_numpy(),
                    table["Y position"].to_numpy(),
                )

            # Outputing the data to the channel files
            functions.exportingToChannelFolder(folderTest, exportData)

            # Displaying the percentage
            currentPercentage = currentTestCount / nTests * 100
            formattedPercentage = f"{currentPercentage:.2f}%"
            print(formattedPercentage, "\t", relativePath, " was processed.")

        except Exception as e:
            # If something failed in the process the script goes to the next test and saves
            # the test in the "failedFiles" list
            failedFiles.append((relativePath, e))
            errorMessage = "There was an error: " + str(e) + "\n"
            errorMessage = errorMessage + relativePath + " was NOT processed"
            functions.decorateSentence(errorMessage, True)


def timeProcess(table, exportData, startTestIndex, testType, test):
    if TestType.DOOR not in testType and TestType.LSS not in testType:
        exportData["10TFCW000000EV00"] = functions.warningProcess(
            table["ADC6"], startTestIndex
        )

    elif TestType.DOOR not in testType:
        exportData["10TECS000000EV00"] = functions.yawVelocityProcess(
            table["Yaw velocity"], startTestIndex
        )

    elif TestType.DOOR in testType:
        exportData["10TWRN000000EV00"] = functions.warningProcess(
            table["ADC6"], startTestIndex
        )

        # I've assumed the ADC7 for the external trigger for the door opening, just use a reference one
        exportData["10TDOP000000EV00"] = functions.warningProcess(
            table["ADC7"], startTestIndex
        )

        testFolder = os.path.dirname(test)

        visualFile = os.path.join(testFolder, "visual.ini")
        if os.path.exists(visualFile):
            with open(visualFile, "r") as file:
                visualValue = file.readline()
            visualValue = float(visualValue)
            print(f"visual.ini was found, the value is: {visualValue}")
            exportData["10TINF000000EV00"] = functions.externalTimeProcess(
                visualValue, table
            )
        else:
            raise ValueError("No visual.ini file was found for the dooring test.")

    elif TestType.LSS in testType:
        testFolder = os.path.dirname(test)
        ldwFile = os.path.join(testFolder, "ldw.ini")
        if os.path.exists(ldwFile):
            with open(ldwFile, "r") as file:
                ldwValue = file.readline()
            ldwValue = float(ldwValue)
            print(f"ldw.ini was found, the value is: {ldwValue}")
            exportData["10TLDW000000EV00"] = functions.externalTimeProcess(
                ldwValue, table
            )
        else:
            functions.decorateSentence(
                "Warning: no ldw.ini file found. Processing the LDW from the ADC6 channel.",
                False,
            )
            exportData["10TLDW000000EV00"] = functions.warningProcess(
                table["ADC6"], startTestIndex
            )


def VUTProcess(table, exportData, testType: List[TestType], folderTest):
    import numpy as np

    # TODO: add a way to import the dimensions dynamically (like from user input or from the .ini file)

    offsetX = 0
    offsetY = 0

    overhang = 2
    width = 2
    x_imu = 3
    y_imu = 0.1

    # TODO: decide if the offset is going to be defined in the motion pack or if you need to calculate it after
    for t in testType:
        match t:
            case TestType.LSS:
                lineFolder = os.path.dirname(folderTest)
                zeroFile = os.path.join(lineFolder, "zero.ini")

                if not os.path.isfile(zeroFile):
                    raise Exception("No zero.ini file was found.")

                with open(zeroFile, "r") as file:
                    zero = file.readline()

                offsetY = -float(zero) + width / 2
                offsetY = 0.0

    vut_yaw_velocity = (
        functions.filtering(table["Yaw velocity"].to_numpy()) * np.pi / 180
    )
    vut_yaw_angle = table["Yaw angle"].to_numpy() * np.pi / 180

    x_position = table["X position"].to_numpy()
    y_position = table["Y position"].to_numpy()

    A = np.array([[overhang], [0], [1]])

    B = np.array([[0], [width / 2], [1]])
    C = np.array([[0], [-width / 2], [1]])

    T_tot = functions.reference_system_change(
        vut_yaw_angle, x_position, y_position, x_imu, y_imu
    )

    T_tot_2 = functions.reference_system_change_3(
        vut_yaw_angle, x_position, y_position, x_imu, y_imu
    )

    # A_new = T_tot @ A
    # B_new = T_tot @ B
    # C_new = T_tot @ C

    A[0:2] = -A[0:2]
    B[0:2] = -B[0:2]
    C[0:2] = -C[0:2]

    A_new = T_tot_2 @ A
    B_new = T_tot_2 @ B
    C_new = T_tot_2 @ C

    exportData["10VEHC000000DSXP"] = A_new[:, 0, 0] + offsetX
    exportData["10VEHC000000DSYP"] = A_new[:, 1, 0] + offsetY

    exportData["10VEHC000000VEXP"] = table["Forward velocity"].to_numpy()
    exportData["10VEHC000000VEYP"] = table["Lateral velocity"].to_numpy()

    exportData["10VEHC000000ACXS"] = functions.filtering(
        table["Forward acceleration"].to_numpy()
    )
    exportData["10VEHC000000ACYS"] = functions.filtering(
        table["Lateral acceleration"].to_numpy()
    )

    exportData["10VEHC000000AVZP"] = vut_yaw_velocity
    exportData["10VEHC000000ANZP"] = vut_yaw_angle

    # TODO CHANGE THE CHANNEL NAME TO RANGE B,C POSITION X,Y
    exportData["11WHEL000000DSXP"] = B_new[:, 0, 0] + offsetX
    exportData["11WHEL000000DSYP"] = B_new[:, 1, 0] + offsetY
    exportData["13WHEL000000DSXP"] = C_new[:, 0, 0] + offsetX
    exportData["13WHEL000000DSYP"] = C_new[:, 1, 0] + offsetY

    sr_velocity = table["SR Velocity"] * np.pi / 180
    sr_angle = table["SR Angle"] * np.pi / 180

    exportData["10STWL000000AV1P"] = sr_velocity
    exportData["10STWL000000AN1P"] = sr_angle

    exportData["10STWL000000MO1P"] = functions.filtering(
        table["SR Column Torque (Estimated)"].to_numpy()
    )

    exportData["10PEAC000000DS0P"] = functions.processAcceleratorPosition(
        table["BR Position"].to_numpy()
    )

    exportData["10PEBR000000DS0P"] = functions.processBrakePosition(
        table["BR Position"].to_numpy()
    )

    exportData["10PEBR000000FO0P"] = table["Brake force (unfiltered)"].to_numpy()

    visualFile = os.path.join(folderTest, "turning_indicator.ini")
    if os.path.exists(visualFile):
        with open(visualFile, "r") as file:
            indicatorValue = file.readline()
        indicatorValue = float(indicatorValue)
        print(f"turning_indicator.ini was found, the value is: {indicatorValue}")
        exportData["110TURN000000EV00"] = functions.externalTimeProcess(
            indicatorValue, table
        )
    else:
        exportData["10TURN000000EV00"] = table["Time"].copy().to_numpy() * 0
        functions.decorateSentence(
            "Warning: no turning_indicator.ini file found. The vector will be all zeros.",
            False,
        )


def VUTProcess_2(table, exportData, testType: List[TestType], folderTest):
    import numpy as np

    # START VUT PROCESS
    #
    # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE_A X POSITION OR WHATEVER
    # TODO ALL THE POSITIONS SHOULD BE ADJUSTED FOR THE CORRECT FRAME OF REFERENCE
    offsetX = 0
    offsetY = 0

    overhang = 2
    width = 2
    x_imu = 3
    y_imu = 0.1

    # THIS IS NOT RIGHT WITH THE NORMAL ZERO, YOU HAVE TO SWTICH BETWEEN GETTING THE ZERO FROM THE NORMAL X AND THE RANGE B OR C POINT
    for t in testType:
        match t:
            case TestType.LSS:
                lineFolder = os.path.dirname(folderTest)
                zeroFile = os.path.join(lineFolder, "zero.ini")

                if not os.path.isfile(zeroFile):
                    raise Exception("No zero.ini file was found.")

                with open(zeroFile, "r") as file:
                    zero = file.readline()

                offsetY = -float(zero) + width / 2
                offsetY = 0.0

    vut_yaw_velocity = (
        functions.filtering(table["Yaw velocity"].to_numpy()) * np.pi / 180
    )
    vut_yaw_angle = table["Yaw angle"].to_numpy() * np.pi / 180

    # CAMBIARE QUEASTO
    vut_yaw_angle = vut_yaw_angle * 0 + 15 * np.pi / 180

    x_position = table["X position"].to_numpy()
    y_position = table["Y position"].to_numpy()

    A = functions.calculate_A(x_imu, y_imu, overhang, vut_yaw_angle)
    B = functions.calculate_B(x_imu, y_imu, width, vut_yaw_angle)
    C = functions.calculate_C(x_imu, y_imu, width, vut_yaw_angle)

    exportData["10VEHC000000DSXP"] = x_position + A[0] * np.cos(A[1])
    exportData["10VEHC000000DSYP"] = y_position + A[0] * np.sin(A[1])

    exportData["10VEHC000000VEXP"] = table["Forward velocity"].to_numpy()
    exportData["10VEHC000000VEYP"] = table["Lateral velocity"].to_numpy()

    exportData["10VEHC000000ACXS"] = functions.filtering(
        table["Forward acceleration"].to_numpy()
    )
    exportData["10VEHC000000ACYS"] = functions.filtering(
        table["Lateral acceleration"].to_numpy()
    )

    exportData["10VEHC000000AVZP"] = vut_yaw_velocity
    exportData["10VEHC000000ANZP"] = vut_yaw_angle

    # TODO CHANGE THE CHANNEL NAME TO RANGE B,C POSITION X,Y
    exportData["11WHEL000000DSXP"] = x_position + B[0] * np.cos(B[1])
    exportData["11WHEL000000DSYP"] = y_position + B[0] * np.sin(B[1])
    exportData["13WHEL000000DSXP"] = x_position + C[0] * np.cos(C[1])
    exportData["13WHEL000000DSYP"] = y_position + C[0] * np.sin(C[1])

    sr_velocity = table["SR Velocity"] * np.pi / 180
    sr_angle = table["SR Angle"] * np.pi / 180

    exportData["10STWL000000AV1P"] = sr_velocity
    exportData["10STWL000000AN1P"] = sr_angle

    exportData["10STWL000000MO1P"] = functions.filtering(
        table["SR Column Torque (Estimated)"].to_numpy()
    )

    exportData["10PEAC000000DS0P"] = functions.processAcceleratorPosition(
        table["BR Position"].to_numpy()
    )

    exportData["10PEBR000000DS0P"] = functions.processBrakePosition(
        table["BR Position"].to_numpy()
    )

    exportData["10PEBR000000FO0P"] = table["Brake force (unfiltered)"].to_numpy()


def targetProcess(table, exportData, testType):
    import numpy as np

    TARGET_CODE = {
        TestType.C2C: "VEHC",
        TestType.C2M: "TWMB",
        TestType.C2B: "CYCL",
        TestType.DOOR: "CYCL",
        TestType.C2PA: "PEDA",
        TestType.C2PC: "PEDC",
    }

    test = None

    for t in testType:
        if t in TARGET_CODE:
            test = t
            break

    if not test:
        return

    # TODO CHANGE THE SYSTEM OF REFERENCE IF NEEDED

    exportData[f"20{TARGET_CODE[test]}000000DSXP"] = table[
        "Target reference X position"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[test]}000000DSYP"] = table[
        "Target reference Y position"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[test]}000000VEXP"] = table[
        "Target forward velocity"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[test]}000000VEYP"] = table[
        "Target lateral velocity"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[test]}000000ACXS"] = functions.filtering(
        table["Target forward acceleration"].to_numpy()
    )

    # Convert Yaw to rad
    target_yaw = table["Target yaw"].to_numpy() * np.pi / 180
    target_yaw_velocity = (
        functions.filtering(table["Target yaw velocity"].to_numpy()) * np.pi / 180
    )

    exportData[f"20{TARGET_CODE[test]}000000ANZS"] = target_yaw
    exportData[f"20{TARGET_CODE[test]}000000AVZP"] = target_yaw_velocity


if __name__ == "__main__":
    main()
