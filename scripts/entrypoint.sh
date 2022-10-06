#!/bin/bash
airflow standalone&
sleep 15
airflow variables set group $LTCFT_RESOURCEGROUP
airflow variables set vmSize $LTCFT_VMSIZE
airflow variables set repoUri $LTCFT_REPOURI
airflow variables set branch $LTCFT_BRANCH
airflow variables set repoPath $LTCFT_REPOPATH
until airflow dags list | grep "Bootstrapper"; do sleep 5; done
airflow dags unpause Bootstrapper
airflow dags trigger Bootstrapper
until airflow dags list-runs --dag-id Bootstrapper | grep "success\|failed"; do sleep 5; done
