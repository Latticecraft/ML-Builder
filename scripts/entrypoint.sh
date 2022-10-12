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
until airflow dags list | grep "Bootstrapper"; do sleep 5; done
airflow dags unpause Bootstrapper
airflow dags trigger Bootstrapper
until airflow dags list-runs --dag-id Bootstrapper | grep "success\|failed"; do sleep 5; done
