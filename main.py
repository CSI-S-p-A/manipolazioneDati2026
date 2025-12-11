import os
import shutil
from io import StringIO

import functions
import test_checks
from test_checks import TestType


def main():
    sourceFolder = functions.getFolder()
    if not sourceFolder:
        return

    parentFolder = os.path.dirname(sourceFolder)
    folderName = os.path.basename(sourceFolder)
    manipulatedFolderName = folderName + "_manipulated"

    print("Copying files...")
    manipulatedFolder = os.path.join(parentFolder, manipulatedFolderName)
    shutil.copytree(sourceFolder, manipulatedFolder, dirs_exist_ok=True)
    print("All files have been copied.\n")

    for root, dirs, files in os.walk(manipulatedFolder, topdown=False):
        for file in files:
            if file.endswith(".txt") and "Current" in file:
                fullPath = os.path.join(root, file)
                os.remove(fullPath)

    txtFiles: list[str] = []
    for root, dirs, files in os.walk(manipulatedFolder):
        for file in files:
            if file.endswith(".txt"):
                fullPath = os.path.join(root, file)
                txtFiles.append(fullPath)

    nTests = len(txtFiles)
    failedFiles: list[tuple[str, Exception]] = []
    currentTestCount = 0

    pd = functions.loadPandas()
    print("Found", nTests, "test files to process.")

    for test in txtFiles:
        currentTestCount += 1
        folderTest = os.path.dirname(test)
        relativePath = test.replace(manipulatedFolder, "")

        if not functions.testCheck(test):
            print(relativePath + " was not a test.")
            os.remove(test)
            continue

        try:
            with open(test, "r") as file:
                fileContent = file.readlines()

            descriptionLines = fileContent[:2]
            numberDataRows = int(descriptionLines[1].split("=")[1].strip())
            totalLines = len(fileContent)
            unitsOfMeasure = fileContent[3]

            headerLines = descriptionLines
            headerLines.append(unitsOfMeasure)

            rowsSkipped = [0, 1, 3] + list(range(4 + numberDataRows, totalLines))

            data = StringIO("".join(fileContent))
            table = pd.read_csv(
                data,
                skiprows=rowsSkipped,
                header=0,
                encoding="cp1252",
                delimiter="\t",
                dtype=float,
            )

            if currentTestCount == 20:
                print(table.columns.values)

            testType = test_checks.testCheck(test)

            dataTime = table["Time"].copy()

            if testType is not test_checks.TestType.LSS:
                dataTTC = table["Time to collision (longitudinal)"]
                [newTime, startTestIndex] = functions.TTCProcess(dataTTC, dataTime)
            else:
                startTestIndex = 500
                print("TODO")
                # TODO here the startTestIndex and new time should be calculated for
                # LSS from different sources, like the steering and the current position on the path

            exportData = {}
            exportData = timeProcess(table, exportData, startTestIndex, testType, test)
            exportData = VUTProcess(table, exportData, testType)
            exportData = targetProcess(table, exportData, testType)

            functions.exportingToChannelFolder(folderTest, exportData)

            # Displaying the percentage
            currentPercentage = currentTestCount / nTests * 100
            formattedPercentage = f"{currentPercentage:.2f}%"
            print(formattedPercentage, "\t", relativePath, " was processed.")

        except Exception as e:
            failedFiles.append((relativePath, e))
            errorMessage = "There was an error: " + str(e) + "\n"
            errorMessage = errorMessage + relativePath + " was NOT processed"
            functions.decorateSentence(errorMessage, True)


def timeProcess(table, exportData, startTestIndex, testType, test):
    if not testType == TestType.DOOR and not testType == TestType.LSS:
        exportData["10TFCW000000EV00"] = functions.warningProcess(
            table["ADC6"], startTestIndex
        )
        exportData["10TECS000000EV00"] = functions.yawVelocityProcess(
            table["Yaw velocity"], startTestIndex
        )
    elif testType == TestType.DOOR:
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
    elif testType == TestType.LSS:
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

    return exportData


def VUTProcess(table, exportData, testType):
    # START VUT PROCESS
    #
    # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE_A X POSITION OR WHATEVER
    # TODO ALL THE POSITIONS SHOULD BE ADJUSTED FOR THE CORRECT FRAME OF REFERENCE
    offsetX = 0
    offsetY = 0

    exportData["10VEHC000000DSXP"] = table["X position"].to_numpy() + offsetX
    exportData["10VEHC000000DSYP"] = table["Y position"].to_numpy() + offsetY

    # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE_A X,Y VELOCITY
    # CHECK FOR UNIT OF MEASURE
    exportData["10VEHC000000VEXP"] = table["Forward velocity"].to_numpy()
    exportData["10VEHC000000VEYP"] = table["Lateral velocity"].to_numpy()

    # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE A X,Y ACCELERATION OR WHATEVER
    exportData["10VEHC000000ACXS"] = functions.filtering(
        table["Forward acceleration"].to_numpy()
    )
    exportData["10VEHC000000ACYS"] = functions.filtering(
        table["Lateral acceleration"].to_numpy()
    )

    exportData["10VEHC000000AVZP"] = functions.filtering(
        table["Yaw velocity"].to_numpy()
    )
    exportData["10VEHC000000ANZP"] = table["Yaw angle"].to_numpy()

    # TODO CHANGE THE CHANNEL NAME TO RANGE B,C POSITION X,Y
    exportData["11WHEL000000DSXP"] = table["X position"].to_numpy() + offsetX
    exportData["13WHEL000000DSYP"] = table["Y position"].to_numpy() + offsetY
    exportData["11WHEL000000DSXP"] = table["X position"].to_numpy() + offsetX
    exportData["13WHEL000000DSYP"] = table["Y position"].to_numpy() + offsetY

    exportData["10STWL000000AV1P"] = table["SR Velocity"]
    exportData["10STWL000000AN1P"] = table["SR Angle"]
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

    return exportData


def targetProcess(table, exportData, testType):
    # TODO CHANGE THE LSS PROCESS
    TARGET_CODE = {
        TestType.LSS: "VEHC",  # Change this
        TestType.C2C: "VEHC",
        TestType.C2M: "TWMB",
        TestType.C2B: "CYCL",
        TestType.DOOR: "CYCL",
        TestType.C2PA: "PEDA",
        TestType.C2PC: "PEDC",
    }

    # TODO CHANGE THE SYSTEM OF REFERENCE
    exportData[f"20{TARGET_CODE[testType]}000000DSXP"] = table[
        "Target reference X position"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[testType]}000000DSYP"] = table[
        "Target reference Y position"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[testType]}000000VEXP"] = table[
        "Target forward velocity"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[testType]}000000VEYP"] = table[
        "Target lateral velocity"
    ].to_numpy()

    exportData[f"20{TARGET_CODE[testType]}000000ACXS"] = functions.filtering(
        table["Target forward acceleration"].to_numpy()
    )

    exportData[f"20{TARGET_CODE[testType]}000000ANZS"] = table["Target yaw"].to_numpy()

    exportData[f"20{TARGET_CODE[testType]}000000AVZP"] = functions.filtering(
        table["Target yaw velocity"].to_numpy()
    )

    return exportData


if __name__ == "__main__":
    main()
