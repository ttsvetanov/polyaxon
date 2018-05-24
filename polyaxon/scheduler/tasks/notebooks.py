import logging

from constants.jobs import JobLifeCycle
from polyaxon.celery_api import app as celery_app
from polyaxon.settings import RunnerCeleryTasks
from db.getters import get_valid_project
from dockerizer import get_notebook_image_info
from scheduler import notebook_scheduler

_logger = logging.getLogger(__name__)


@celery_app.task(name=RunnerCeleryTasks.PROJECTS_NOTEBOOK_START, ignore_result=True)
def projects_notebook_start(project_id):
    project = get_valid_project(project_id)
    if not project or not project.notebook:
        _logger.warning('Project does not have a notebook.')
        return None

    if project.notebook.last_status == JobLifeCycle.RUNNING:
        _logger.warning('Tensorboard is already running.')
        return None

    try:
        image_name, image_tag = get_notebook_image_info(project=project, job=project.notebook)
    except ValueError as e:
        _logger.warning('Could not start the notebook, %s', e)
        return
    job_docker_image = '{}:{}'.format(image_name, image_tag)
    _logger.info('Start notebook with built image `%s`', job_docker_image)

    notebook_scheduler.start_notebook(project, image=job_docker_image)


@celery_app.task(name=RunnerCeleryTasks.PROJECTS_NOTEBOOK_STOP, ignore_result=True)
def projects_notebook_stop(project_id):
    project = get_valid_project(project_id)
    if not project:
        return None

    notebook_scheduler.stop_notebook(project, update_status=True)