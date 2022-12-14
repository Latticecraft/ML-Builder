import os, argparse
import subprocess

from airflow import DAG, XComArg
from airflow.decorators import dag, task, task_group
from airflow.models import Variable
from airflow.models.baseoperator import chain
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime


def git_clone_accel():
    return BashOperator(
        task_id='git_clone_accel',
        bash_command='mkdir {{var.value.accelRepoPath}}; git clone --branch {{var.value.accelBranch}} {{var.value.accelRepoUri}} {{var.value.accelRepoPath}}', 
        start_date=datetime.now())

def git_clone_dash():
    return BashOperator(
        task_id='git_clone_dash',
        bash_command='mkdir {{var.value.dashRepoPath}}; git clone --branch {{var.value.dashBranch}} {{var.value.dashRepoUri}} {{var.value.dashRepoPath}}', 
        start_date=datetime.now())

def login():
    return BashOperator(
        task_id='login',
        bash_command='az login --identity', 
        start_date=datetime.now())

def deploy_arm():
    return BashOperator(
        task_id='deploy_arm',
        bash_command='az deployment group create --resource-group {{var.value.group}} --template-file {{var.value.accelRepoPath}}/config/resourcegroup/azuredeploy-accelerator.json --parameters vmSize={{var.value.vmSize}}', 
        start_date=datetime.now())

def get_location():
    return BashOperator(
        task_id='get_location',
        bash_command='az group show --name {{var.value.group}} --query "location"', 
        start_date=datetime.now())

def get_workspace_name():
    return BashOperator(
        task_id='get_workspace_name',
        bash_command='az ml workspace list --query "[].{Name:name}[0].Name" --resource-group {{var.value.group}}', 
        start_date=datetime.now())

def set_defaults():
    return BashOperator(
        task_id='set_defaults',
        bash_command='az configure --defaults group={{var.value.group}} workspace={{task_instance.xcom_pull("get_workspace_name")}} location={{task_instance.xcom_pull("get_location")}}', 
        start_date=datetime.now())

def create_env():
    return BashOperator(
        task_id='create_env',
        bash_command='az ml environment create --name lgbmholoenv --version 1 --build-context {{var.value.accelRepoPath}}/config/environment/ --dockerfile-path lgbmholoenv.Dockerfile',
        start_date=datetime.now())

def build_env():
    return BashOperator(
        task_id='build_env',
        bash_command='az ml job create --file {{var.value.accelRepoPath}}/config/pipeline/buildenv.yaml --stream',
        start_date=datetime.now())

def create_compute():
    return BashOperator(
        task_id='create_compute',
        bash_command='az ml compute create --name cpu-cluster --size {{var.value.vmSize}} --min-instances 0 --max-instances 1 --type AmlCompute --resource-group {{var.value.group}} --workspace-name {{task_instance.xcom_pull("get_workspace_name")}}',
        start_date=datetime.now())

def wait_for_compute():
    return BashOperator(
        task_id='wait_for_compute',
        bash_command='until az ml compute show --name cpu-cluster --query provisioning_state --resource-group {{var.value.group}} --workspace-name {{task_instance.xcom_pull("get_workspace_name")}} | grep "Succeeded"; do sleep 1; done',
        start_date=datetime.now())

def run_default_experiments():
    run_default = Variable.get('runDefaultExperiments')
    if run_default == 'True':
        return 'default_experiments.download_data'
    else:
        return 'do_nothing'

@task
def do_nothing():
    return

def download_data():
    return BashOperator(
        task_id='download_data',
        bash_command='mkdir {{var.value.accelRepoPath}}/data; curl --output {{var.value.accelRepoPath}}/data/Bank_Campaign.csv https://ltcftwebaiprod.blob.core.windows.net/datasets/Bank_Campaign.csv',
        start_date=datetime.now())

def upload_data():
    return BashOperator(
        task_id='upload_data',
        bash_command='az ml data create --datastore input --name Bank_Campaign --path {{var.value.accelRepoPath}}/data/Bank_Campaign.csv --version 1 --type uri_file',
        start_date=datetime.now())

def get_data_path():
    return BashOperator(
        task_id='get_data_path',
        bash_command='az ml data show --name Bank_Campaign --version 1 --query path',
        start_date=datetime.now())

def run_featurize():
    return BashOperator(
        task_id='featurize',
        bash_command='python {{var.value.accelRepoPath}}/src/commands/featurize.py --project Bank-Campaign --type Binary --input {{task_instance.xcom_pull("default_experiments.get_data_path")}} --label subscribed --replacements %7B%22yes%22%3Atrue%2C%22no%22%3Afalse%7D --datatypes %7B%22default%22%3A%22bool%22%2C%22housing%22%3A%22bool%22%2C%22loan%22%3A%22bool%22%7D --separator semicolon --filename featurize-gen.yaml --run True',
        start_date=datetime.now())

def run_train():
    return BashOperator(
        task_id='train',
        bash_command='python {{var.value.accelRepoPath}}/src/commands/train.py --project Bank-Campaign --type Binary --primary-metric weighted-avg_f1-score --label subscribed --source "https://www.kaggle.com/datasets/pankajbhowmik/bank-marketing-campaign-subscriptions" --imputers knn --balancers ros --num-trials 5 --filename train-gen.yaml --run True',
        start_date=datetime.now())

def run_dashboard():
    return BashOperator(
        task_id='update_dashboard',
        bash_command='python {{var.value.dashRepoPath}}/src/commands/update_dashboard.py --project Bank-Campaign --type Binary --primary-metric weighted-avg_f1-score --label subscribed',
        start_date=datetime.now())

@task_group(group_id='default_experiments')
def taskgroup_defaultexps():
    download_data() >> \
    upload_data() >> \
    get_data_path() >> \
    run_featurize() >> \
    run_train() >> \
    run_dashboard()

# DAG
@dag(schedule_interval=None, start_date=datetime(2022,1,1), catchup=False)
def MLBuilder():
    git_clone_accel() >> \
    git_clone_dash() >> \
    login() >> \
    deploy_arm() >> \
    get_workspace_name() >> \
    set_defaults() >> \
    create_compute() >> \
    wait_for_compute() >> \
    create_env() >> \
    build_env() >> \
    BranchPythonOperator(
        task_id='run_default_experiments',
        python_callable=run_default_experiments) >> [
            do_nothing(),
            taskgroup_defaultexps()
        ]
    

# run main function
dag1 = MLBuilder()
dag1