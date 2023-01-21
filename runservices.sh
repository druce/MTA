#!/bin/bash --login
# services that run at login

########################################
# start ssh service
########################################
sudo service ssh start

########################################
# run jupyter
########################################
cd /mnt
export PYTHONPATH=/mnt
set -e
source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
conda activate mds
jupyter notebook --no-browser &

########################################
# run MLflow
########################################
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
# mlflow server --default-artifact-root /mnt/mlruns --host 0.0.0.0 &

########################################
# run airflow
########################################

# airflow scheduler -D & 
# airflow webserver -D &

########################################
# run superset
########################################
# superset run -p 8088 --with-threads --reload --debugger

sleep 2
echo
echo "######################################################################"
echo Jupyter \(password 'emergent'\) https://localhost:8888
echo MLflow http://localhost:5000
echo ssh \(password 'emergent'\) ubuntu@localhost -p 2222
echo "######################################################################"
