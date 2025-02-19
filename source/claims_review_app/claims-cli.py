import boto3
import os
import sys
import argparse
import uuid
import time
from prettytable import PrettyTable
from datetime import datetime, timezone
import dateutil.parser
import json
import botocore
from botocore.exceptions import CredentialRetrievalError, NoRegionError
# from typing import Optional       if using python version < 3.10
class ClaimsCLI:
    def __init__(self):
        try :
            self.cf_client = boto3.client('cloudformation')
            self.s3_client = boto3.client('s3')
            self.bedrock_agent_client = boto3.client('bedrock-agent')
            self.stack_name = 'claims-review'  # Replace with your actual stack name
        except CredentialRetrievalError as cre:
            print("""Oops! It looks like we couldn't find your AWS credentials. Please make sure you've set up your AWS access key and secret key correctly. Need help? Check out the AWS documentation on credential configuration!
                          """)
        except NoRegionError as re:
            print("""Oops! It looks like we couldn't find your AWS region. Please make sure you've set up your default AWS region along with AWS access key and secret key correctly. Need help? Check out the AWS documentation on credential configuration!
                          """)
            sys.exit(1)

    def start_ingestion_job(self, bucket, key):
        response = self.bedrock_agent_client.start_ingestion_job(
            dataSourceId=self.get_eoc_kb_datasource_id,
            knowledgeBaseId=self.get_eoc_kb_id,
            description=f"Knowledge Base Sync triggered for S3: Bucket={bucket}, key={key}"
        )
        return response['ingestionJob']['ingestionJobId']


    def get_ingestion_job_for_document(self, bucket:str, key:str, timestamp):
        kb_id = self.get_eoc_kb_id()
        datasource_id = self.get_eoc_kb_datasource_id()
        response  = self.bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=kb_id,
            dataSourceId=datasource_id
        )
        jobs = response["ingestionJobSummaries"]
        jobs = [item for item in jobs if item['startedAt'] >= timestamp]
        jobs = sorted(jobs, key=lambda x: x['startedAt'], reverse=True)
        return next((job for job in jobs if (bucket in job['description'] and key in job['description'])), None)
    
    def list_ingestion_jobs(self):
        kb_id = self.get_eoc_kb_id()
        datasource_id = self.get_eoc_kb_datasource_id()
        response  = self.bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=kb_id,
            dataSourceId=datasource_id
        )
        jobs = sorted(response["ingestionJobSummaries"], key=lambda x: x['startedAt'], reverse=True)
                # Create a PrettyTable object
        table = PrettyTable()
        # Define the columns for your table
        # Adjust these based on the actual keys in the response
        table.field_names = ["Ingestion Job Id", "Status", "# New Documents Indexed", "StartTime", "End Time"]

        # Add rows to the table
        for job in jobs:
            table.add_row([
                job.get('Ingestion Job Id', job["ingestionJobId"]),
                job.get('Status', job['status']),
                job.get('#Documents Indexed', job['statistics']["numberOfNewDocumentsIndexed"]),
                job.get('StartTime', job['startedAt']),
                job.get('Last Updated', job['updatedAt'])
            ])

        print(table)

    def get_ingestion_job_status(self,ingestion_job_id:str):
        response  = self.bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=self.get_eoc_kb_id(),
            dataSourceId=self.get_eoc_kb_datasource_id(),
            ingestionJobId=ingestion_job_id
        )
        return response['ingestionJob']['status']

    
    # def wait_for_start(self,bucket:str, key:str,timestamp, max_attempts=10, delay=5)-> Optional[str]:  if using python version < 3.10
    def wait_for_start(self,bucket:str, key:str,timestamp, max_attempts=10, delay=5)-> None | str:
        attempts = 0
        while attempts < max_attempts:
            job = self.get_ingestion_job_for_document(bucket, key, timestamp)
            if not job:
                print(f"Attempt {attempts + 1}: Waiting for the Ingestion Job to start.")
            else:
                print("Ingestion Job Started successfully!")
                return job['ingestionJobId']
            
            attempts += 1
            time.sleep(delay)
        print("Max attempts reached. Ingestion Job for the document did not start. It is possible that the document is still vectorized by another Sync job")
        return None

    def wait_for_ingestion_job_completion(self,ingestion_job_id, max_attempts=10, delay=5):
        attempts = 0
        while attempts < max_attempts:
            status = self.get_ingestion_job_status(ingestion_job_id)
            if status in ['COMPLETE', 'FAILED','STOPPED']:
                return True
            print(f"Attempt {attempts + 1}: Waiting for Job to complete. Current status is {status}")
            attempts += 1
            time.sleep(delay)
        print("Max attempts reached. Task not completed.")
        return False


    def generate_claim_reference_id(self):
        return str(uuid.uuid4())
    
    def get_stack_output(self, export_name:str):
        response = self.cf_client.describe_stacks(StackName=self.stack_name)
        output = None
        try:
            output = next((item["OutputValue"] for item in response['Stacks'][0]['Outputs'] if item.get('ExportName')==export_name), None)
        except:
            raise ValueError(f"Output with Export Name '{export_name}' not found in stack")
        return output

    def get_eoc_kb_datasource_id(self)-> str:
        return self.get_stack_output(export_name = 'claims-eoc-kb-datsource-id') # type: ignore

    def get_claims_review_agent_id(self)-> str:
        return self.get_stack_output(export_name = 'claims-review-agent-id') # type: ignore

    def get_claims_review_agent_alias_id(self)-> str:
        return self.get_stack_output(export_name = 'claims-review-agent-alias-id') # type: ignore

    def get_eoc_kb_id(self)-> str:
        return self.get_stack_output(export_name = 'claims-eoc-kb-id') # type: ignore

    def get_claims_submission_bucket_name(self)-> str:
        return self.get_stack_output(export_name = 'claims-submission-bucket') # type: ignore

    def get_claims_review_bucket_name(self)-> str:
        return self.get_stack_output(export_name = 'claims-review-bucket') # type: ignore

    def get_eoc_bucket_name(self)->str:
        return self.get_stack_output(export_name = 'claims-eoc-kb-datasource-bucket') # type: ignore

    def submit_claim(self, claim_form_path, bucket_name):
        if not os.path.exists(claim_form_path):
            print(f"Error: File '{claim_form_path}' does not exist.")
            return

        try:
            file_name = os.path.basename(claim_form_path)
            claim_reference_id = self.generate_claim_reference_id()
            key = f"{claim_reference_id}/{claim_form_path.split('/')[-1]}"
            self.s3_client.upload_file(claim_form_path, bucket_name, key)
            print(f"\n\033[1mClaim form submitted. Claim reference Id: {claim_reference_id}\033[0m\n")
        except Exception as e:
            print(f"Error uploading file: {str(e)}")

    def print_job_status(self, ingestion_job_id):
            print(f"\n\033[1m Ingestion Job with Id {ingestion_job_id} {self.get_ingestion_job_status(ingestion_job_id)}\033[0m\n")

    def add_eoc_document(self, eoc_document_path:str, bucket_name:str):
        if not os.path.exists(eoc_document_path):
            print(f"Error: File '{eoc_document_path}' does not exist.")
            return

        try:
            key = os.path.basename(eoc_document_path)
            #get current timestamp
            timestamp = datetime.now(timezone.utc)
            self.s3_client.upload_file(eoc_document_path, bucket_name, key)
            print(f"\n\033[1mUploaded document.... Running Datasource Sync\033[0m\n")
            ingestion_job_id = self.wait_for_start(bucket_name, key, timestamp)
            self.print_job_status(ingestion_job_id)
            self.wait_for_ingestion_job_completion(ingestion_job_id)
            self.print_job_status(ingestion_job_id)

        except Exception as e:
            print(f"Error uploading file: {str(e)}")

    def list_claims(self):
        bucket_name = self.get_claims_submission_bucket_name()        
        # Initialize S3 client
        s3_client = boto3.client('s3')

        try:
            # List objects with delimiter to get only first-level prefixes
            result = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')

            if 'CommonPrefixes' in result:
                print("\n\033[1mClaim Reference IDs:\033[0m")
                for prefix in result['CommonPrefixes']:
                    # Remove the trailing slash to get the claim reference ID
                    claim_id = prefix['Prefix'].rstrip('/')
                    print(f"•\t{claim_id}")
                print("\n")
            else:
                print(f"\n\033[1mNo claims found in the bucket.\033[0m")
        except Exception as e:
            print(f"Error listing claims: {str(e)}")

    def check_deployment_status(self):
        try:
            response = self.cf_client.describe_stacks(StackName=self.stack_name)
            print(f"Stack Deployment is {response['Stacks'][0]['StackStatus']}.")
        except self.cf_client.exceptions.ClientError as e:
            print(f"Error describing stack: {str(e)}")
            return False
        

    def view_claim_output(self, claim_reference_id:str):
        print("\n\033[1mClaim Output:\033[0m")
        try:
            claim_output_s3_object = self.s3_client.get_object(
                Bucket=self.get_claims_review_bucket_name(),
                Key=f"{claim_reference_id}/claim_output.json")
        except self.s3_client.exceptions.NoSuchKey as e:
            print(f"Error: Claim output not found for claim reference ID: {claim_reference_id}. Please try again later.")
            return

        claim_output = json.loads(claim_output_s3_object['Body'].read().decode('utf-8'))
        print(claim_output)
        print("\n")
def main():

    cli = ClaimsCLI()

    parser = argparse.ArgumentParser(description="Claims CLI", usage="claims_cli <action> [<args>]")
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')

    # Subparser for submit-claim
    parser_submit = subparsers.add_parser('submit-claim', help='Submit a new claim')
    parser_submit.add_argument('--file', required=True, help="File path for the claim to submit")

    # Subparser for upload-eoc-document
    parser_upload = subparsers.add_parser('upload-eoc-document', help='Upload an EOC document')
    parser_upload.add_argument('--file', required=True, help="File path for the EOC document to upload")

    # Subparser for view-claim-status
    parser_view = subparsers.add_parser('view-claim-output', help='View the output of a claim')
    parser_view.add_argument('--claim-reference-id', required=True, help="Claim Reference ID of the claim to view")

    parser_list_ingestion_jobs = subparsers.add_parser('list-ingestion-jobs', help='View Ingestion Jobs')

    parser_list_claims = subparsers.add_parser('list-claims', help='List all claim reference IDs')

    parser_check_deployment_status = subparsers.add_parser('check-deployment-status', help='Output the claims review stack deployment status')

    # Parse arguments
    args = parser.parse_args()

    parser.add_argument('action', help='Action to perform is required. Either submit-claim upload-eoc-document')

    # If no action is provided, print help
    if not args.action:
        parser.print_help()
        sys.exit(1)

    # Subparser for each action
    if args.action == 'submit-claim':
        action_parser = argparse.ArgumentParser(description="Submit a claim")
        action_parser.add_argument('--file', required=True, help="File path for the claim form")
        bucket_name = cli.get_claims_submission_bucket_name()
        cli.submit_claim(args.file, bucket_name)

    elif args.action == 'upload-eoc-document':
        action_parser = argparse.ArgumentParser(description="Upload an EOC document")
        action_parser.add_argument('--file', required=True, help="File path for the EOC document")
        cli.add_eoc_document(
            eoc_document_path=args.file,
            bucket_name=cli.get_eoc_bucket_name()
        )
    elif args.action == 'list-claims':
        cli.list_claims()

    elif args.action == 'check-deployment-status':
        cli.check_deployment_status()

    elif args.action == 'view-claim-output':
        action_parser = argparse.ArgumentParser(description="View Claim Output")
        action_parser.add_argument('--claim_reference_id', required=True, help="Claim Reference Id")
        cli.view_claim_output(args.claim_reference_id)
    elif args.action == 'list-ingestion-jobs':
            cli.list_ingestion_jobs()
    else:
        print(f"Unknown action: {args.action}")
        parser.print_help(sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
