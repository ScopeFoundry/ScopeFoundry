#! /bin/bash
# ScopeFoundry/plugin_manager/scripts/subtree_hw.sh
# subtree pushes a module in ScopeFoundryHW/ to ScopeFoundry/plugin_manager/my_repos/
# args: <module_name>
# 2023-02-13 Benedikt Ursprung

cd ..
cd ..
root=$PWD

current_branch=$(git rev-parse --abbrev-ref HEAD)
# echo the current branch is $current_branch

my_repo_path="ScopeFoundry/plugin_manager/my_hw_repos"
path_HW_git="$my_repo_path/HW_$1.git"

# echo attempting to pull subtree from $subtree to
# echo $path_HW_git

# echo mkdir $path_HW_git
mkdir $path_HW_git

cd $path_HW_git
git init --bare

echo $path_HW_git

# last_commit=$(git log -1 --pretty=format:"%h")
# echo $last_commit

cd $root
# echo subtree push --prefix "ScopeFoundryHW/$1" $path_HW_git $current_branch
git subtree push --prefix "ScopeFoundryHW/$1" $path_HW_git $current_branch

cd $my_repo_path
git clone HW_$1.git/
# cd HW_$1
# git checkout $current_branch
