module_name=$1
gh_repo=$2

cd my_hw_repos/$module_name
current_branch=$(git rev-parse --abbrev-ref HEAD)
# echo current_branch $current_branch

# echo create public repo on github
gh repo create $module_name --public

# echo attempting to push to $gh_repo
git remote add github $gh_repo

git push github $current_branch
