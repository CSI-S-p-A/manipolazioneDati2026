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

            index_ADC5 = table.columns.get_loc("ADC5")
            if type(index_ADC5) is int:
                table.rename(
                    columns={table.columns[index_ADC5 + 1]: "ADC6"}, inplace=True
                )

            if currentTestCount == 20:
                print(table.columns.values)

            testType = test_checks.testCheck(test)

            dataTime = table["Time"].copy()

            if test_checks.TestType.LSS not in testType:
                dataTTC = table["Time to collision (longitudinal)"]
                [newTime, startTestIndex] = functions.TTCProcess(dataTTC, dataTime)
            else:
                # TODO here the startTestIndex and new time should be calculated for
                # LSS from different sources, like the steering and the current position on the path
                startTestIndex = 500

            # Filling the channels
            exportData = {}
            timeProcess(table, exportData, startTestIndex, testType, test)
            VUTProcess(table, exportData, testType, folderTest)

            print(exportData["10VEHC000000DSXP"])

            if currentTestCount == 1:
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

            targetProcess(table, exportData, testType)

            # Outputing the data to the channel files
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
    if TestType.DOOR not in testType and TestType.LSS not in testType:
        exportData["10TFCW000000EV00"] = functions.warningProcess(
            table["ADC6"], startTestIndex
        )
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


# KEEP FIXING THIS PLEASE
def VUTProcess(table, exportData, testType: List[TestType], folderTest):
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

    # TODO CHANGE THE LSS PROCESS
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
