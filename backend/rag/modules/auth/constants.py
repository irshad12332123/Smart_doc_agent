from enum import StrEnum


class RegistryType(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"


class GlobalRole(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class StudentRole(StrEnum):
    REGULAR = "regular"
    CLASS_REPRESENTATIVE = "cr"


AuthorizedRolesToAcessUpload = {
    StudentRole.CLASS_REPRESENTATIVE,
    GlobalRole.FACULTY,
}


REGISTRY_CONFIG = {
    RegistryType.STUDENT: {
        "table": "students",
        "email_columns": ["official_email", "registered_email"],
        "role": GlobalRole.STUDENT,
    },
    RegistryType.FACULTY: {
        "table": "faculty",
        "email_columns": ["registered_email", "official_email"],
        "role": GlobalRole.FACULTY,
    },
}
