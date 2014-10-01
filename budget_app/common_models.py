from django.core.urlresolvers import reverse
from django.db import models

import logging
logger = logging.getLogger(__name__)

################ Common ################

class StampedModel(models.Model):
    "Model with time stamps"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SequencedModel(StampedModel):
    "Model with sequence number (and time stamps)"
    seq = models.PositiveIntegerField(default=10)

    class Meta:
        abstract = True

################ People ################

class Person(StampedModel):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True)

    home_phone = models.CharField(max_length=20, blank=True)
    cell_phone = models.CharField(max_length=20, blank=True)
    work_phone = models.CharField(max_length=20, blank=True)

    photo = models.ImageField(upload_to='photos',blank=True)

    class Meta:
        verbose_name_plural = 'people'

    def __unicode__(self):
        return self.full_name

    @property
    def full_name(self):
        return '{0} {1}'.format(self.first_name, self.last_name)

    def get_absolute_url(self):
        return reverse('common_person_detail', args=[str(self.pk)])
