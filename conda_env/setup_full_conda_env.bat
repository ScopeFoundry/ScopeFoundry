call deactivate
conda remove --name scopefoundry --all -y
REM conda create --name scopefoundry python=2 anaconda=4.2.0 -y
conda env create -f scopefoundry_full.yml
