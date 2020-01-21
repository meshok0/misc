#!/usr/bin/env python3

import argparse
import os
import time
import redis
import boto3


def parse_args():
    parser = argparse.ArgumentParser(description='Reads a hash from redis and writes its content to AWS SSM Parameter Store interactively')
    parser.add_argument(
        '--redis-host',
        default=os.environ.get('REDIS_HOST', 'localhost'))
    parser.add_argument(
        '--redis-port',
        default=os.environ.get('REDIS_PORT', '6379'))
    parser.add_argument(
        '--redis-key',
        default=os.environ.get('REDIS_KEY', 'key'),
        help='Must be a hash')
    parser.add_argument(
        '--kms-key',
        default=os.environ.get('KMS_KEY', 'kms-key'),
        help='AWS KMS key id or alias to encrypt values')

    args = parser.parse_args()
    return args


if __name__ == "__main__":
  args = parse_args()
  redis_host = args.redis_host
  redis_key = args.redis_key
  kms_key = args.kms_key

  redis = redis.Redis(redis_host)
  ssm = boto3.client("ssm")

  params = redis.hgetall(redis_key)


  for key in params:
    key_decoded = key.decode()
    val_decoded = (lambda val: val.decode() if val else 'NULL' )(params[key])
    print("%s = %s" % (key_decoded, val_decoded) )
    check = str(input("Encode value? (y/n) ")).lower().strip()
    if check[0] == 'y':
      encode = True
    else:
      encode = False

    ssm_put_args = { 
      'Name': key_decoded,
      'Value': val_decoded,
      'Overwrite': True,
      'Type': 'String' 
    }

    if encode:
      ssm_put_args['Type'] = 'SecureString'
      ssm_put_args['KeyId'] = kms_key

    while True:
      try:
        response = ssm.put_parameter(**ssm_put_args)
        break
      except Exception as e:
        print(str(e))
        time.sleep(2)
        print("Retrying...")
        continue
