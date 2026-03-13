from django.db import models


class ActivityLogAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    UPDATE = "UPDATE", "Update"
    APPROVE = "APPROVE", "Approve"
    CANCEL = "CANCEL", "Cancel"
    DELETE = "DELETE", "Delete"

class ActivityLogModel(models.TextChoices):
    DOCTOR = "DOCTOR", "Doctor"
    EXAMINATION = "EXAMINATION", "Examination"
    EXAMINATION_PACK = "EXAMINATION_PACK", "Examination pack"
    EXAMINATION_TYPE = "EXAMINATION_TYPE", "Examination type"
    ORDER = "ORDER ", "Order"