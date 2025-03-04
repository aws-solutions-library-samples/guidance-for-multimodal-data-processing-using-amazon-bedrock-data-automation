import boto3
import uuid
from bedrock_agent_runtime_wrapper import BedrockAgentRuntimeWrapper
import os
import json
from urllib.parse import urlparse
import re
import string
import random

agent_runtime = boto3.client('bedrock-agent-runtime')
agent_runtime_wrapper = BedrockAgentRuntimeWrapper(agent_runtime)

CLAIMS_REVIEW_AGENT_ID = os.environ["CLAIMS_REVIEW_AGENT_ID"]
CLAIMS_REVIEW_AGENT_ALIAS_ID = os.environ["CLAIMS_REVIEW_AGENT_ALIAS_ID"]
ERROR_MESSAGE = "Our system is currently unable to complete this task. Please attempt to submit your claim again in approximately 5-10 minutes. If you continue to experience difficulties, we kindly request that you contact our customer support team for further assistance. We appreciate your patience and understanding as we work to resolve this issue"

s3 = boto3.client("s3")

class CustomOutputNotFoundError(Exception):
    """Raised when a the custom output is not found"""
    pass

class InsightJobFailed(Exception):
    """Raised when the insight job status was not success"""
    pass

#function to generate custom unique Id
def generate_unique_id():
    return str(uuid.uuid4())

def invoke_bedrock_agent(claim_reference_id:str, s3_uri:str):
    try:
        session_id = claim_reference_id
        agent_output = agent_runtime_wrapper.invoke_agent(
            agent_id=CLAIMS_REVIEW_AGENT_ID,
            agent_alias_id=CLAIMS_REVIEW_AGENT_ALIAS_ID,
            session_id =  session_id,
            prompt=f"Review the claim using claim form data in S3 URI {s3_uri}"
        )
        # Process the response
        return agent_output
        
    except Exception as e:
        print(f"Error invoking Bedrock agent: {str(e)}")
        return  ERROR_MESSAGE
    
def lambda_handler(event, context):
    # Log the event for debugging
    print(f"Received event: {event}")
    claim_reference_id = extract_claim_reference_id(event)
    processed_automation_output_uri = extract_document_automation_output(event,context)
    # Invoke Bedrock agent
    agent_response = invoke_bedrock_agent(claim_reference_id, processed_automation_output_uri)

    # Log the response for debugging
    print(f"Bedrock agent response: {agent_response}")
    output_s3_location_s3_bucket = event["detail"]["output_s3_location"]["s3_bucket"]
    
    extracted_output = s3.put_object(
        Bucket=output_s3_location_s3_bucket,
        Key=f"{claim_reference_id}/claim_output.json",
        Body=json.dumps(agent_response)
    )    
    # Return the response to the caller
    return {
        'statusCode': 200,
        'body': agent_response
    }

def extract_claim_reference_id(event):
    input_s3_object_key = event["detail"]["input_s3_object"]["name"]
    #extract claim reference id from input_s3_object_key
    claim_reference_id = input_s3_object_key.split("/")[0]
    return claim_reference_id

def extract_document_automation_output(event, context):

    #if the detail.job_status in event is not SUCCESS then throw error
    if event["detail"]["job_status"] != "SUCCESS":
        raise InsightJobFailed(f"Couldn't get insights from claim form for claim ref: {claim_reference_id}")

    input_s3_object_key = event["detail"]["input_s3_object"]["name"]

    claim_reference_id = extract_claim_reference_id(event)
    output_s3_location = event["detail"]["output_s3_location"]
    output_s3_location_s3_bucket = output_s3_location["s3_bucket"]
    output_s3_location_key = output_s3_location["name"].rsplit("/",1)[0]
    assetId = output_s3_location["name"].rsplit("/",1)[1]

    #read s3 object job_metadata.json from the  output_s3_location_uri
    job_metadata = json.loads(s3.get_object(Bucket=output_s3_location_s3_bucket, 
                                 Key=f"{output_s3_location_key}/job_metadata.json")["Body"].read().decode("utf-8"))

    if not job_metadata["output_metadata"]:
        raise CustomOutputNotFoundError(f"Couldn't find custom output for claim ref: {claim_reference_id}")
    try:
        custom_output_path = next(item["segment_metadata"][0]["custom_output_path"] 
                                for item in job_metadata["output_metadata"] 
                                if str(item['asset_id']) == assetId)
    except StopIteration:
        raise CustomOutputNotFoundError(
            f"Could not find matching asset_id '{assetId}' in job metadata output for claim ref: {claim_reference_id}"
        )

    parsed_uri = urlparse(custom_output_path)
    custom_output_bucket_name = parsed_uri.netloc
    custom_output_object_key = parsed_uri.path.lstrip('/')
    custom_output_s3_object = s3.get_object(Bucket=custom_output_bucket_name,
                                 Key=custom_output_object_key)

    custom_output = json.loads(custom_output_s3_object['Body'].read().decode('utf-8'))
    inference_result = custom_output["inference_result"]

    #put inference results to s3
    extracted_output = s3.put_object(
        Bucket=output_s3_location_s3_bucket,
        Key=f"{input_s3_object_key}.json",
        Body=json.dumps(inference_result)
    )
    return f"s3://{output_s3_location_s3_bucket}/{input_s3_object_key}.json"
