import boto3
import os
from botocore.exceptions import ClientError

BUCKET_NAME = 'genai-bedrock-udemy-virginia-01'
FILES_TO_UPLOAD = [
    ('openapi/schema.json', 'openapi/schema.json'),
    ('prompts/prompt-ecomm.txt', 'prompts/prompt-ecomm.txt')
]


def ensure_bucket_exists(s3_client, bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': s3_client.meta.region_name}
            )
            print(f"Bucket '{bucket_name}' created.")
        else:
            raise


def upload_files(s3_client, bucket_name, files):
    for local_path, s3_key in files:
        if not os.path.exists(local_path):
            print(f"File not found: {local_path}")
            continue
        s3_client.upload_file(local_path, bucket_name, s3_key)
        print(f"Uploaded {local_path} to s3://{bucket_name}/{s3_key}")


def main():
    s3_client = boto3.client('s3')
    ensure_bucket_exists(s3_client, BUCKET_NAME)
    upload_files(s3_client, BUCKET_NAME, FILES_TO_UPLOAD)

if __name__ == '__main__':
    main()
