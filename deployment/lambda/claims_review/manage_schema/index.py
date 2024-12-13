import boto3
import os
import json

rds_data_client = boto3.client('rds-data')
s3_client = boto3.client('s3')
cluster_arn = os.environ['CLUSTER_ARN']
secret_arn = os.environ['SECRET_ARN']
database_name = os.environ['DATABASE_NAME']
create_schema_sql_file = os.environ['CREATE_SCHEMA_FILE']
delete_schema_sql_file = os.environ['DELETE_SCHEMA_FILE']
update_schema_sql_file = os.environ.get('UPDATE_SCHEMA_FILE',None)
initial_data_sql_file = os.environ.get('INITIAL_DATA_FILE', None)

def handler(event, context):
    
    print(event)
    request_type = event['RequestType']
    match request_type:
        case 'Create':
            execute(create_schema_sql_file)
            if initial_data_sql_file:
                execute(initial_data_sql_file)
        case 'Update':
            if update_schema_sql_file:
                execute(update_schema_sql_file)
        case 'Delete':
            execute(delete_schema_sql_file)
        case _:
          raise ValueError(f"Invalid request type: {request_type}")
    

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully executed {request_type} operation')
    }

def execute(sql_file_path:str):
    """Create the schema in the database."""

    # Download SQL script from S3
    bucket_name, key_name = parse_s3_url(sql_file_path)
    
    sql_script = download_sql_script(bucket_name, key_name)
    
    # Split script into individual statements and execute each one
    statements = sql_script.split(';')
    
    for statement in statements:
        if statement.strip():
            # Execute each statement
            print(f"Executing statement: {statement}")
            execute_statement(cluster_arn, secret_arn, database_name, statement)

def parse_s3_url(s3_url):
    """Parse S3 URL into bucket name and key."""
    s3_url_parts = s3_url.replace("s3://", "").split("/", 1)
    return s3_url_parts[0], s3_url_parts[1]

def download_sql_script(bucket_name, key_name):
    """Download SQL script from S3."""
    response = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    return response['Body'].read().decode('utf-8')

def execute_statement(cluster_arn, secret_arn, database_name, sql_statement):
    """Execute a single SQL statement using RDS Data API."""
    response = rds_data_client.execute_statement(
        resourceArn=cluster_arn,
        secretArn=secret_arn,
        database=database_name,
        sql=sql_statement
    )

