import os
from pathlib import Path
import subprocess


def publish_hw(
    github_username,
    subfolder,
    subfolder_path,
    message="Initial commit",
    private_or_public="--public",
):
    print(f"Processing folder: {subfolder}")

    # Initialize a Git repository if not already initialized

    if not os.path.exists(os.path.join(subfolder_path, ".git")):
        subprocess.run(["git", "init"], cwd=subfolder_path)

    subprocess.run(["git", "branch", "-m", "main"], cwd=subfolder_path)
    # Add all files and commit
    subprocess.run(["git", "add", "."], cwd=subfolder_path)
    subprocess.run(["git", "commit", "-m", message], cwd=subfolder_path)

    # Create a GitHub repository using GitHub CLI
    repo_name = subfolder
    subprocess.run(
        [
            "gh",
            "repo",
            "create",
            f"{github_username}/HW_{repo_name}",
            private_or_public,
            "--source",
            subfolder_path,
            "--push",
        ],
        cwd=subfolder_path,
    )
    # Push the local repository to GitHub

    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            f"https://github.com/{github_username}/HW_{repo_name}.git",
        ],
        cwd=subfolder_path,
    )

    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=subfolder_path)

    print(f"Published {subfolder} as a GitHub repository.")


def publish_subfolders_as_repos(parent_dir, github_username):
    """
    Publishes each subfolder in the given directory as a separate GitHub repository.

    Parameters:
    - parent_dir: Path to the parent directory containing subfolders.
    - github_username: Your GitHub username.
    """
    for subfolder in os.listdir(parent_dir):
        subfolder_path = os.path.join(parent_dir, subfolder)

        # Skip if not a directory
        if not os.path.isdir(subfolder_path):
            continue

        publish_hw(github_username, subfolder, subfolder_path)


if __name__ == "__main__":
    parent_directory = Path(__file__).parent  # Adjust this to your parent directory
    gh_username = "ubene"  # Replace with your GitHub username
    publish_subfolders_as_repos(parent_directory, gh_username)
