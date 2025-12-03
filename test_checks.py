import os
from enum import Enum, auto


class TestType(Enum):
    LSS = auto()
    C2C = auto()
    C2M = auto()
    C2B = auto()
    DOOR = auto()
    C2PA = auto()
    C2PC = auto()


# TODO
# I'm just doing a partial check here just for debugging
# Maybe just "CC" or "CB" should work for most of the checks
# Need to also distinguish from LSS without the target and LSS with the target


def testCheck(test: str) -> TestType:
    specTest = test.replace(".txt", ".spec")

    IDENTIFIERS = {
        TestType.LSS: ("LKA", "ELK", "LDW"),  # Update with the new LSS
        TestType.C2C: ("CCRs", "CCRm", "CCRb", "CCFhos", "CCFtap", "CCC"),
        TestType.C2M: ("CMRs", "CMRb", "CMF", "CMC"),
        TestType.C2B: ("CBNA", "CBFA", "CBNAO", "CBLA", "CBTA"),
        TestType.DOOR: ("CBDA",),
        TestType.C2PA: ("CPLA", "CPNA", "CPFA", "CPTA"),
        TestType.C2PC: ("CPNC",),
    }

    with open(specTest, "r") as specFile:
        descriptionLine = specFile.readlines()[1]

    for testType, indentifers in IDENTIFIERS.items():
        if any(i in descriptionLine for i in indentifers):
            print(testType)
            return testType

    raise ValueError("No matching was found for the test type, check the .spec file")
