import datetime
import logging
import os
import csv

from airflow import settings
from airflow.models import DAG, DagModel
from airflow.operators.python import PythonOperator
from airflow.operators.email_operator import EmailOperator
from airflow.utils.email import send_email
from datetime import datetime, timedelta
from google.cloud import storage
from airflow.configuration import conf
from airflow.models import Variable


environment = Variable.get('platform_composer_env')
email_subject_prefix = "GCP "+environment+' '+"clear root files"
to_emails = ['your_email@example.com']  # Replace with appropriate email address
var3 = conf.get("webserver", "web_server_name")

DAG_ID = 'monthly_clear_unused_dag_info'
deleted_list = []
var1=conf.get("webserver", "web_server_name")

import importlib
import re

def report_failure(context):
    send_email = EmailOperator(
                    task_id = 'failure_email',
                    to = to_emails,
                    subject = f'{email_subject_prefix} Clearing dags task failed',
                    html_content = f"""
                    Hello Team, <br>
                    <br>
                    The monthly job {var3}.{DAG_ID} for clearing DAGs with no corresponding python in bucket has been failed.<br>
                    <br>
                    Thanks<br>
		    		<br>Runbook:<br><href>LINK</href>
                    
                    """,
                    dag=dag                    
                    )

    send_email.execute(context)

default_args = {
		'owner':'airflow', 
		'depends_on_past':False, 
		'start_date':'ANY START DATE',
		'email_on_failure':True,
		'on_failure_callback':report_failure, 
		'retries': 2,
    	'retry_delay': timedelta(minutes=5),}

dag = DAG(DAG_ID, default_args=default_args, schedule_interval="0 18 1 * *")

def monthly_clear_unused_dag_info():

	session = settings.Session()

	dags = session.query(DagModel).all()
	deleted_list.append({'dag_id': 'Dag_ID', 'file_path': 'File_Path', 'environment':'Environment Name'})
	for dag in dags:
		logging.info (dag.dag_id + '   ' + dag.fileloc)
		file_location = dag.fileloc
		if not os.path.exists (file_location) : 
			deleted_list.append({'dag_id': dag.dag_id, 'file_path' : file_location, 'environment':var1})
			logging.info ('dag has to be deleted' + '  ' + dag.dag_id)
			session.query(DagModel).filter(DagModel.dag_id==dag.dag_id).delete()
			session.commit()

	keys = deleted_list[0].keys()
	storage_client = storage.Client()
	if Variable.get('platform_composer_env')=='preprod':
		env_bucket='prod'
	else:
		env_bucket=Variable.get('platform_composer_env')
	bucket_name = "YOUR BUCKET NAME"+env_bucket
	file_name = "deleted_list_"
	ct1 = datetime.now()
	outfile = 'composer/jobs'+'/'+var1+'/'+DAG_ID+'/'+file_name+str(ct1.strftime("%Y%m%d%H%M%S")) + '.csv'
	bucket = storage_client.bucket(bucket_name)
	blob = bucket.blob((outfile))
	with blob.open(mode='w') as output_file:
		dict_writer = csv.DictWriter(output_file,keys,delimiter=";")
		dict_writer.writerows(deleted_list)

clear_dag = PythonOperator(task_id = 'Clear_Dag', python_callable=monthly_clear_unused_dag_info, dag=dag, provide_context=True)

