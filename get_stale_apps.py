#!/usr/bin/env python3

import boto3
import kubernetes
from datetime import datetime, timezone
from os import environ
import json
import sys
import csv

ecr_registry_id = environ.get('ECR_REGISTRY_ID', '555555555555')
ecr_days_left_threshold = environ.get('ECR_DAYS_LEFT_THRESHOLD', 10)
print_csv_header = environ.get('PRINT_CSV_HEADER', 'true')

kubernetes.config.load_kube_config()
k8s_client = kubernetes.client.AppsV1Api()
ecr_client = boto3.client('ecr')

deployments = k8s_client.list_deployment_for_all_namespaces(watch=False)

result = []

for deployment in deployments.items:
  for container in deployment.spec.template.spec.containers:
    ## filter images to incude only from our ECR
    if container.image.startswith(ecr_registry_id):
      repository_full=container.image.split(':')[0]
      repository=repository_full.split('/')[1]
      tag=container.image.split(':')[1]

      ## get lifecycle policy of an ECR repo and extract retention period
      retention_period_days = -1
      try:
        lifecycle_policy = json.loads(ecr_client.get_lifecycle_policy(
          registryId=ecr_registry_id,
          repositoryName=repository
        )['lifecyclePolicyText'])
        for rule in lifecycle_policy['rules']:
          if rule['action']['type'] == 'expire' and rule['selection']['tagStatus'] == 'any' and rule['selection']['countType'] == 'sinceImagePushed' and rule['selection']['countUnit'] == 'days':
            retention_period_days = rule['selection']['countNumber']
      except ecr_client.exceptions.LifecyclePolicyNotFoundException:
        pass
      ## just ignore missing repos
      except ecr_client.exceptions.RepositoryNotFoundException:
        continue
      
      ## get push date of an image
      try:
        ecr_image = ecr_client.describe_images(
          registryId=ecr_registry_id,
          repositoryName=repository,
          imageIds=[
            {
              'imageTag': tag
            },
          ]
        )
      ## if already absent
      except ecr_client.exceptions.ImageNotFoundException:
        #print('no tag')
        days_left = 0
      ## if the image is still there calculate its days left
      else:
        date_pushed = ecr_image['imageDetails'][0]['imagePushedAt'].astimezone(timezone.utc)
        date_now = datetime.now(timezone.utc)
        date_delta = date_now - date_pushed
        days_left = retention_period_days - date_delta.days

      ## decide whether to append the image to the results; retention_period_days is less then -1 if there is no LC policy
      if -1 < days_left < ecr_days_left_threshold:
        result.append([ deployment.metadata.name, repository, tag, days_left ])
        #result.append({'deployment': deployment.metadata.name, 'ecr_repo': repository, 'ecr_tag': tag, 'days_left': days_left})
        #print("App: {deployment}\nECR repo: {image}\nECR tag: {tag}\nDays left: {days_left}\n".format(deployment=deployment.metadata.name, image=repository, tag=tag, days_left=days_left))


## print the result as json
#result_json = json.dumps(result, indent=2)
#print(result_json)

## print the result as csv
csv_out=csv.writer(sys.stdout)
if print_csv_header.lower() == 'true':
  csv_out.writerow(['deployment', 'ecr_repo', 'ecr_tag', 'days_left'])
for row in result:
  csv_out.writerow(row)
