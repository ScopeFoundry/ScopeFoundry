#! /bin/bash
# ScopeFoundry/plugin_manager/scripts/subtree_hw.sh
# merges a git_repo to tree and places files in subdir_path, remote_name somewhat arbitrary.
# 2023-02-13 Benedikt Ursprung

# args
remote_name=$1
git_repo=$2 
destination_dir=$3

cd ..
cd ..
ls
git rm --cached $destination_dir -r
git remote add -f $remote_name $git_repo
git merge -s ours --no-commit --allow-unrelated-histories $remote_name/master
git read-tree --prefix=$destination_dir -u $remote_name/master
# git commit -m "Subtree merged in $remote_name"
# git merge $remote_name/master --allow-unrelated-histories

