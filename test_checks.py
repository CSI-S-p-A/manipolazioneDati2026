from enum import Enum, auto
from pathlib import Path
from typing import List


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
# Maybe just "CC" or "CM" should work for most of the checks
# NOT "CB" (Dooringe exists)
# NOT "CP" (Child scenarios exist)
# Need to also distinguish from LSS without the target and LSS with the target


def testCheck(test: str) -> List[TestType]:
    specTest = Path(test).with_suffix(".spec")

    matches = []

    IDENTIFIERS = {
        TestType.LSS: ("LKA", "ELK", "LDW"),  # Update with the new LSS
        TestType.C2C: ("CCRs", "CCRm", "CCRb", "CCFhos", "CCFtap", "CCC", "VUT"),
        TestType.C2M: ("CMRs", "CMRb", "CMF", "CMC", "EMT"),
        TestType.C2B: ("CBNA", "CBFA", "CBNAO", "CBLA", "CBTA"),
        TestType.DOOR: ("CBDA",),
        TestType.C2PA: ("CPLA", "CPNA", "CPFA", "CPTA", "CPRA"),
        TestType.C2PC: ("CPNC", "CPRC", "CPMFC", "CPMRC"),
    }

    with open(specTest, "r") as specFile:
        descriptionLine = specFile.readlines()[1]

    for testType, identifers in IDENTIFIERS.items():
        if any(i in descriptionLine for i in identifers):
            print(testType)
            matches.append(testType)

    if matches:
        return matches

    raise ValueError("No matching was found for the test type, check the .spec file")
