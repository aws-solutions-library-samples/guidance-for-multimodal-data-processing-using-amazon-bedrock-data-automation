import string
from random import random

import boto3
import json
import os
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

ENDPOINT_RUNTIME = os.environ.get('BDA_RUNTIME_ENDPOINT', None)

# Create a Bedrock client
bda_client_runtime = boto3.client("bedrock-data-automation-runtime",
                                **({'endpoint_url': ENDPOINT_RUNTIME} if ENDPOINT_RUNTIME is not None else {}),
                                verify=True)

# allows to call the bda api directly, until the SDK gets released, then we can replace it with boto3 methods
def bda_sdk(bda_client_runtime, url_path ="data-automation-projects/", method ="POST", service ="bedrock", payload={}, control_plane = True):
    host = bda_client_runtime.meta.endpoint_url.replace("https://", "")
    url = f"{bda_client_runtime.meta.endpoint_url}/{url_path}"
    if control_plane:
        host = host.replace(".runtime", "")
        url = url.replace(".runtime", "")
    session = boto3.Session()

    request = AWSRequest(
        method,
        url,
        headers={'Host': host}
    )

    region = bda_client_runtime.meta.region_name
    SigV4Auth(session.get_credentials(), service, region).add_auth(request)
    headers = dict(request.headers)
    print(headers)
    response = requests.request(method, url, headers=headers, data=payload, timeout=5)
    print(response)
    content = response.content.decode("utf-8")
    data = json.loads(content)
    return data

# get the project arn based on the name
def get_project_arn(project_name):
    list_results = bda_sdk(bda_client_runtime=bda_client_runtime, url_path="data-automation-projects/", method="POST",
                           payload={})
    # get the project arn
    projects_filtered = [item for item in list_results["projects"] if project_name == item["projectName"]]
    if len(projects_filtered) == 0:
        raise Exception(f"Project {project_name} not found")
    project_arn = projects_filtered[0]["projectArn"]
    return project_arn

# invokes bda by async approach with a given pdf input file
def invoke_insight_generation_async(
        input_s3_uri,
        output_s3_uri,
        data_project_arn, blueprints = None):

    payload = {
        "inputConfiguration": {
            "s3Uri": input_s3_uri
        },
        "outputConfiguration": {
            "s3Uri": output_s3_uri
        },
        "dataAutomationConfiguration": {
            "dataAutomationArn": data_project_arn,
        },
        "NotificationConfiguration": {
        "EventBridgeConfiguration": {"EventBridgeEnabled": True},
        }
    # "blueprints" : [
        # {"blueprintArn": blueprint_arn}
        # ]
    }

    response = bda_client_runtime.invoke_data_automation_async(**payload)
    print(response)
    return response
