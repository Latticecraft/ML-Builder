#!/bin/bash
airflow standalone&
sleep 15
airflow variables set group $LTCFT_RESOURCEGROUP
airflow variables set vmSize $LTCFT_VMSIZE
airflow variables set accelRepoUri $LTCFT_ACCELREPOURI
airflow variables set accelBranch $LTCFT_ACCELBRANCH
airflow variables set dashRepoUri $LTCFT_DASHREPOURI
airflow variables set dashBranch $LTCFT_DASHBRANCH
airflow variables set accelRepoPath $LTCFT_ACCELREPOPATH
airflow variables set dashRepoPath $LTCFT_DASHREPOPATH
airflow variables set runDefaultExperiments $LTCFT_RUNDEFAULTEXPERIMENTS
until airflow dags list | grep "MLBuilder"; do sleep 5; done
airflow dags unpause MLBuilder
airflow dags trigger MLBuilder
until airflow dags list-runs --dag-id MLBuilder | grep "success\|failed"; do sleep 5; done