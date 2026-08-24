from enum import StrEnum


class RegistryType(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"


class GlobalRole(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class StudentRole(StrEnum):
    REGULAR="regular"
    CLASS_REPRESENTATIVE="cr"


REGISTRY_CONFIG = {
    RegistryType.STUDENT: {
        "table": "students",
        "identifier_column": "student_id",
        "role": GlobalRole.STUDENT,
    },
    RegistryType.FACULTY: {
        "table": "faculty",
        "identifier_column": "faculty_id",
        "role": GlobalRole.FACULTY,
    },
}
