from .import_from_gh_qt_view import ImportFromGhView as View
from .utils import InfoTypes, decorate_info_text, run_subprocess


class ImportFromGhController:
    def __init__(self, view: View):
        self.view = view
        # self.view.validate_my_gh_acc_validate_clicked(self.validate_my_gh_acc)
        self.view.validate_origin_repo_clicked(self.validate_origin_repo)
        self.view.fork_clicked(self.fork_on_gh)
        self.view.import_clicked(self.import_from_origin)
        self.view.validate_fork_clicked(self.validate_fork)
        self.view.import_from_fork_clicked(self.import_from_fork)

        self.view.set_ready_to_import(False)
        self.view.set_ready_to_import_from_fork(False)

    def set_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.set_info_text(text)

    def append_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.append_info(text)

    def new_task_msg(self, text):
        self.set_msg(text, InfoTypes.TASK)

    def validate_my_gh_acc(self):
        raise NotImplementedError
        # no necessary
        # self.set_info('validating my acc')
        # self.view.set_my_gh_acc_valid(True)

    def validate_origin_repo(self):
        origin_repo = self.view.get_origin_repo()
        self.new_task_msg(f'validating origin repo {origin_repo}')
        success = self.check_exists_and_report(origin_repo)
        # self.view.set_origin_repo_valid(success)
        self.view.set_ready_to_import(success)

    def import_from_origin(self):
        origin_repo = self.view.get_origin_repo()
        name = origin_repo.split('/')[-1].strip('.git').strip('HW_')
        destination_dir = f"ScopeFoundryHW/{name}"
        self.import_repo(origin_repo, destination_dir)

    def fork_on_gh(self):
        origin_repo = self.view.get_origin_repo()

        stdout, stderr = fork_on_gh(origin_repo)
        self.append_msg(stdout, InfoTypes.INFO)
        self.append_msg(stderr, InfoTypes.ERROR)
        self.validate_fork()

    def import_from_fork(self):
        origin_repo = self.view.get_origin_repo()
        name = origin_repo.split('/')[-1].strip('.git').strip('HW_')
        my_gh_acc = self.view.get_my_gh_acc()

        repo_to_import = f"https://github.com/{my_gh_acc}/HW_{name}.git"
        destination_dir = f"ScopeFoundryHW/{name}"
        self.new_task_msg(f'importing {repo_to_import} to {destination_dir}')
        self.import_repo(repo_to_import, destination_dir)

    def validate_fork(self):
        my_gh_acc = self.view.get_my_gh_acc()
        origin_repo = self.view.get_origin_repo()
        module_name = origin_repo.split('/')[-1].strip('.git')

        forked_repo = f"https://github.com/{my_gh_acc}/{module_name}"
        self.new_task_msg(f'validating fork repo {forked_repo}')
        success = self.check_exists_and_report(forked_repo)
        self.view.set_ready_to_import_from_fork(success)

    def import_repo(self, repo_to_import, destination_dir):
        remote_name = repo_to_import.split('/')[-1].strip('.git')
        stdout, stderr = subtree_merge_strategy(
            remote_name, repo_to_import, destination_dir)
        self.append_msg(stdout, InfoTypes.INFO)
        self.append_msg(stderr, InfoTypes.ERROR)

    def check_exists_and_report(self, repo):
        stdout, stderr = ls_repo(repo)
        exists = stderr == ""
        if exists:
            self.append_msg(f"repo exists: {repo}", InfoTypes.SUCCESS)
        else:
            self.append_msg(f"repo does NOT exist {repo}", InfoTypes.FAILED)
            # self.append_info(stdout, InfoTypes.INFO)
            self.append_msg(stderr, InfoTypes.ERROR)
        return exists


def fork_on_gh(origin_repo):
    return run_subprocess(f"gh repo fork {origin_repo} --remote=True")


def ls_repo(repo="https://github.com/ScopeFoundry/HW_picam.git"):
    cmd = f"git ls-remote {repo}"
    return run_subprocess(cmd)


def subtree_merge_strategy(remote_name, repo_to_import, destination_dir):
    cmd = f"bash scripts/merge_remote_tree_with_subdir.sh {remote_name} {repo_to_import} {destination_dir}"
    return run_subprocess(cmd)
