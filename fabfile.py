from pathlib import Path
from fabric.api import local, task, lcd, env

proj_p = Path(env.real_fabfile).parent


@task
def update():
    with lcd(proj_p.as_posix()):
        local('python gen_ical.py')
        local('cp index.html output/')
        local('ghp-import -p output/')
