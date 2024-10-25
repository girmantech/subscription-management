import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import json
from os import environ

load_dotenv()

def get_secret():
    secret_name = environ.get('DB_SECRET_NAME')
    region_name = environ.get('DB_REGION')

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = json.loads(get_secret_value_response['SecretString'])
    return secret
