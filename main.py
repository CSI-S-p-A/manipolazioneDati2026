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

            numberOfColumns = len(table.columns)

            if currentTestCount == 20:
                print(table.columns.values)

            test_checks.testCheck(test)

        except Exception as e:
            failedFiles.append((relativePath, e))
            errorMessage = "There was an error: " + str(e) + "\n"
            errorMessage = errorMessage + relativePath + "was NOT processed"
            functions.decorateSentence(errorMessage, True)


if __name__ == "__main__":
    main()
