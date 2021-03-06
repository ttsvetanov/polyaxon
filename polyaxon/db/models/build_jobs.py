import logging

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property

from db.models.abstract_jobs import AbstractJob, AbstractJobStatus, JobMixin
from docker_images.images_tags import LATEST_IMAGE_TAG
from libs.spec_validation import validate_build_spec_config
from polyaxon_schemas.polyaxonfile.specification import BuildSpecification

logger = logging.getLogger('db.build_jobs')


class BuildJob(AbstractJob, JobMixin):
    """A model that represents the configuration for build job."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='+')
    project = models.ForeignKey(
        'db.Project',
        on_delete=models.CASCADE,
        related_name='build_jobs')
    config = JSONField(
        help_text='The compiled polyaxonfile for the build job.',
        validators=[validate_build_spec_config])
    code_reference = models.ForeignKey(
        'db.CodeReference',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+')
    dockerfile = models.TextField(
        blank=True,
        null=True,
        help_text='The dockerfile used to create the image with this job.')
    status = models.OneToOneField(
        'db.BuildJobStatus',
        related_name='+',
        blank=True,
        null=True,
        editable=True,
        on_delete=models.SET_NULL)

    class Meta:
        app_label = 'db'

    def __str__(self):
        return '{}.builds.{}'.format(self.project.unique_name, self.sequence)

    def save(self, *args, **kwargs):  # pylint:disable=arguments-differ
        if self.pk is None:
            last = BuildJob.objects.filter(project=self.project).last()
            self.sequence = 1
            if last:
                self.sequence = last.sequence + 1

        super(BuildJob, self).save(*args, **kwargs)

    @cached_property
    def specification(self):
        return BuildSpecification(values=self.config)

    def set_status(self, status, message=None, details=None):  # pylint:disable=arguments-differ
        return self._set_status(status_model=BuildJobStatus,
                                logger=logger,
                                status=status,
                                message=message,
                                details=details)

    @staticmethod
    def create(user, project, config, code_reference, nocache=False):
        build_config = BuildSpecification.create_specification(config, to_dict=False)
        if not nocache and build_config.build.nocache is not None:
            # Set the config's nocache rebuild
            nocache = build_config.build.nocache
        # Check if image is not using latest tag, then we can reuse a previous build
        if not nocache and build_config.build.image_tag != LATEST_IMAGE_TAG:
            job = BuildJob.objects.filter(project=project,
                                          config=build_config.parsed_data,
                                          code_reference=code_reference).last()
            if job:
                return job

        return BuildJob.objects.create(user=user,
                                       project=project,
                                       config=build_config.parsed_data,
                                       code_reference=code_reference)


class BuildJobStatus(AbstractJobStatus):
    """A model that represents build job status at certain time."""
    job = models.ForeignKey(
        'db.BuildJob',
        on_delete=models.CASCADE,
        related_name='statuses')

    class Meta(AbstractJobStatus.Meta):
        app_label = 'db'
        verbose_name_plural = 'Build Job Statuses'
