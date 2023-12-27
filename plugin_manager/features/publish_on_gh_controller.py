from pathlib import Path
import pathlib

from ScopeFoundry import plugin_manager

from .publish_on_gh_view import PublishOnGhView as View
from .utils import InfoTypes, decorate_info_text, run_subprocess


class PublishOnGhController:
    def __init__(self, view: View):
        self.view = view
        view.update_hw_options_clicked(self.update_hw_options)
        view.subtree_clicked(self.subtree_hw)
        view.publish_clicked(self.publish_on_gh)
        self.update_hw_options()

    def set_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.set_info_text(text)

    def append_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.append_info(text)

    def new_task_msg(self, text):
        self.set_msg(text, InfoTypes.TASK)

    def update_hw_options(self):
        hw_path = Path("../../ScopeFoundryHW/")
        print(hw_path)
        if not hw_path.is_dir():
            hw_path.mkdir()
        print([p.name for p in hw_path.iterdir()])
        self.view.set_hw_options([p.name for p in hw_path.iterdir()])

    def subtree_hw(self):
        name = self.view.get_hw()
        module_name = f"HW_{name}"

        self.new_task_msg(f"attempting to subtree {module_name}")
        path = Path(f"../my_hw_repos/{module_name}.git")
        if path.is_dir():
            self.append_msg(
                f"Path {path} already exists use push instead", InfoTypes.FAILED
            )
            return

        stdout, stderr = subtree_hw(name)
        self.append_msg(stdout, InfoTypes.INFO)
        self.append_msg(stderr, InfoTypes.ERROR)
        # self.publish_on_gh()

    def publish_on_gh(self):
        name = self.view.get_hw()
        module_name = f"HW_{name}"
        my_gh_acc = self.view.get_my_gh_acc()
        gh_repo = f"https://github.com/{my_gh_acc}/{module_name}.git"

        if self.repo_exist(gh_repo):
            self.append_msg(f"repo already exists: {gh_repo}", InfoTypes.FAILED)
            return

        self.new_task_msg(f"publish {gh_repo}")
        stdout, stderr = publish_on_gh(module_name, gh_repo)
        self.append_msg(stdout, InfoTypes.INFO)
        self.append_msg(stderr, InfoTypes.ERROR)

    def repo_exist(self, repo):
        stdout, stderr = ls_remote(repo)
        return stderr == ""


def ls_remote(repo):
    cmd = f"git ls-remote -h {repo}"
    return run_subprocess(cmd)


def subtree_hw(name):
    cmd = f"bash scripts/subtree_hw.sh {name}"
    return run_subprocess(cmd)


# def publish_on_gh(module_name, gh_repo):
#     cmd = f"bash scripts/publish_on_gh.sh {module_name} {gh_repo}"
#     return run_subprocess(cmd)


def publish_on_gh(module_name, gh_repo):
    current_branch, stderr = run_subprocess(f"git rev-parse --abbrev-ref HEAD")
    # path = pathlib.Path(f"plugin_manager/my_hw_repos/{module_name}")
    path = pathlib.Path(f"my_hw_repos/{module_name}")
    if not path.exists():
        path.mkdir()

    print(path.absolute().as_posix())
    cmds = [
        f"dir\n",
        f"cd my_hw_repos/\n",
        f"dir\n",
        # f'cd "{path.absolute().as_posix()}"',
        # f"gh repo create {module_name} --public",
        # f"git remote add github {gh_repo}",
        # f"git push github {current_branch}",
    ]
    stdout, stderr = run_subprocess(cmds)
    return stdout, stderr

    # # current_branch=$(git rev-parse --abbrev-ref HEAD)
    # # echo current_branch $current_branch

    # # echo create public repo on github
    # gh repo create $module_name --public

    # # echo attempting to push to $gh_repo
    # git remote add github $gh_repo

    # git push github $current_branch
