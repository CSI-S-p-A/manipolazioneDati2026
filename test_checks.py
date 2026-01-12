from enum import Enum, auto
from pathlib import Path
from typing import List


# This is the way to define Enums in Python, it's just a way to encode the possible test types
class TestType(Enum):
    LSS = auto()
    C2C = auto()
    C2M = auto()
    C2B = auto()
    DOOR = auto()
    C2PA = auto()
    C2PC = auto()


def testCheck(test: str) -> List[TestType]:
    # Analizing the .spec file
    specTest = Path(test).with_suffix(".spec")

    matches = []

    # Associate the identifiers with the test types
    # TODO add a "needs the turning indicator" type to Overtaking and TAP
    IDENTIFIERS = {
        TestType.LSS: ("LKA", "ELK", "LDW"),  # Update with the new LSS
        TestType.C2C: (
            "CCRs",
            "CCRm",
            "CCRb",
            "CCFhos",
            "CCFtap",
            "CCC",
            "VUT",
            "Overtaking",
        ),
        TestType.C2M: ("CMRs", "CMRb", "CMF", "CMC", "EMT", "CMO"),
        TestType.C2B: ("CBNA", "CBFA", "CBNAO", "CBLA", "CBTA"),
        TestType.DOOR: ("CBDA",),
        TestType.C2PA: ("CPLA", "CPNA", "CPFA", "CPTA", "CPRA"),
        TestType.C2PC: ("CPNC", "CPRC", "CPMFC", "CPMRC"),
    }

    with open(specTest, "r") as specFile:
        descriptionLine = specFile.readlines()[1]

    # For every test type it tries to match from the words in the second line of the spec file (descriptionLine)
    # the match can work also for more that one word
    for testType, identifers in IDENTIFIERS.items():
        if any(i in descriptionLine for i in identifers):
            print(testType)
            matches.append(testType)

    if matches:
        return matches

    # If it doesn't find any match it panics and it doesn't complete the processing
    raise ValueError("No matching was found for the test type, check the .spec file")
