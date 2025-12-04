import os
import shutil
from io import StringIO

import functions
import test_checks


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

            exportData = {}

            numberOfColumns = len(table.columns)

            if currentTestCount == 20:
                print(table.columns.values)

            testType = test_checks.testCheck(test)

            dataTime = table["Time"].copy()

            if testType is not test_checks.TestType.LSS:
                dataTTC = table["Time To Collision (Longitudinal)"]
                [newTime, startTestIndex] = functions.TTCProcess(dataTTC, dataTime)
            else:
                print("TODO")
                # here the startTestIndex and new time should be calculated for
                # LSS from different sources, like the steering and the current position on the path

            # START VUT PROCESS
            #
            # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE A X POSITION OR WHATEVER
            # TODO ALL THE POSITIONS SHOULD BE ADJUSTED FOR THE CORRECT FRAME OF REFERENCE
            exportData["10VEHC000000DSXP"] = table["X position"]
            exportData["10VEHC000000DSYP"] = table["Y position"]

            # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE A X,Y VELOCITY
            # CHECK FOR UNIT OF MEASURE
            exportData["10VEHC000000VEXP"] = table["Forward velocity"]
            exportData["10VEHC000000VEYP"] = table["Lateral velocity"]

            # TODO CHANGE THE CHANNEL NAME CHANGE IT TO RANGE A X,Y ACCELERATION OR WHATEVER
            exportData["10VEHC000000ACXS"] = functions.filtering(
                ["Forward acceleration"]
            )
            exportData["10VEHC000000ACYS"] = functions.filtering(
                ["Lateral acceleration"]
            )

            exportData["10VEHC000000AVZP"] = functions.filtering(["Yaw velocity"])
            exportData["10VEHC000000ANZP"] = table["Yaw angle"]

            # TODO CHANGE THE CHANNEL NAME TO RANGE B,C POSITION X,Y
            exportData["11WHEL000000DSXP"] = table["X position"]
            exportData["13WHEL000000DSYP"] = table["Y position"]
            exportData["11WHEL000000DSXP"] = table["X position"]
            exportData["13WHEL000000DSYP"] = table["Y position"]

            exportData["10STWL000000AV1P"] = table["SR Velocity"]
            exportData["10STWL000000AN1P"] = table["SR Angle"]
            exportData["10STWL000000MO1P"] = functions.filtering(
                ["SR Column Torque (estimated)"]
            )

            exportData["10PEAC000000DS0P"] = functions.processAcceleratorPosition(
                table["BR position"]
            )

            exportData["10PEBR000000DS0P"] = functions.processBrakePosition(
                table["BR position"]
            )

            exportData["10PEBR000000FO0P"] = table["Brake Force"]

            currentPercentage = currentTestCount / nTests * 100
            formattedPercentage = f"{currentPercentage:.2f}%"
            print(formattedPercentage, "\t", relativePath, "was processed.")

        except Exception as e:
            failedFiles.append((relativePath, e))
            errorMessage = "There was an error: " + str(e) + "\n"
            errorMessage = errorMessage + relativePath + "was NOT processed"
            functions.decorateSentence(errorMessage, True)


if __name__ == "__main__":
    main()
