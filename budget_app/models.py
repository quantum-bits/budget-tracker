from django.db import models

from common_models import *
from campus_models import *

import logging
logger = logging.getLogger(__name__)

"""    
class RequirementBlock(models.Model):
    ANDREQ = 1
    ORREQ = 2
    AND_OR_CHOICES = (
        (ANDREQ, 'AND'),
        (ORREQ, 'OR')
    )

    name = models.CharField(max_length=50,
                            help_text="e.g., PhysicsBS Technical Electives, or GenEd Literature;"
                            "first part is helpful for searching (when creating a major).")
    
    display_name = models.CharField(max_length=50,
                                    help_text="e.g., Technical Electives, or Literature;"
                                    "this is the title that will show up when students"
                                    "do a graduation audit.")

    requirement_type  = models.IntegerField(choices=AND_OR_CHOICES, default = ANDREQ,
                                                help_text = "Choose AND if all are required,"
                                                "OR if a subset is required.")

    minimum_number_of_credit_hours = models.IntegerField(default = 10)
    
    list_order = models.PositiveIntegerField(default = 1,
                                             help_text="Preferred place in the list"
                                             "of requirements; it is OK if numbers"
                                             "are repeated or skipped.")
    
    text_for_user = models.CharField(max_length=200, blank = True,
                                     help_text="Optional helpful text for the user;"
                                     "will appear in the graduation audit.")
    
    courses = models.ManyToManyField(Course, help_text = "Select courses for this requirement.")

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
"""

# class StudentSemesterCourses
#
# This class used to represent courses taken by a student in a given semester. In the
# updated data model, this relationship is captured in the CourseTaken model, which
# relates a Student to CourseOffering. The CourseOffering has an associated Semester
# object, which tells us when the student took that course.


# class CreateYourOwnCourse
#
# This class has been replaced by the more sensibly-named TransferCourse.
