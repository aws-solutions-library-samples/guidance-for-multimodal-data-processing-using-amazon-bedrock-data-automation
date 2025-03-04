import boto3
import json

class InvalidRequestTypeError(ValueError):
    pass

    
# Create a Bedrock client
bda_client = boto3.client("bedrock-data-automation")
s3 = boto3.client("s3")
def update_blueprint(physical_resource_id:str, resourceProperties):

    if "blueprintStage" not in resourceProperties:
        raise ValueError("blueprintStage not provided in the resource properties")

    response = bda_client.update_blueprint(
        blueprintArn=physical_resource_id,
        schema=load_blueprint_schema(resourceProperties),
        blueprintStage=resourceProperties["blueprintStage"],
    )
    return  response["blueprint"]


def delete_blueprint(event):
    print(event)
    physical_resource_id = event["PhysicalResourceId"]
    print("delete resource %s" % physical_resource_id)
    response = bda_client.delete_blueprint(
        blueprintArn=physical_resource_id
    )
    print(response)

def on_event(event, context):
    """
    This function is the entry point for the Lambda function.
    It receives an event and a context object, and based on the request type
    in the event, it calls the appropriate function to handle the request.
    """
    print(event)
    request_type = event['RequestType']
    if request_type == 'Create': return on_create(event)
    if request_type == 'Update': return on_update(event)
    if request_type == 'Delete': return on_delete(event)
    raise InvalidRequestTypeError(f"Invalid request type: {request_type}")

def load_blueprint_schema(resourceProperties):
    if "BlueprintSchemaUri" not in resourceProperties:
        raise ValueError("BlueprintSchemaUri not provided in the resource properties")

    blueprintSchema = s3.get_object(
        Bucket=resourceProperties["BlueprintSchemaUri"].split("/",3)[2], 
        Key=resourceProperties["BlueprintSchemaUri"].split("/",3)[3])["Body"].read().decode("utf-8")
    return blueprintSchema


def create_blueprint(resourceProperties):

    if "BlueprintName" not in resourceProperties:
        raise ValueError("BlueprintName not provided in the resource properties")

    response = bda_client.create_blueprint(
        blueprintName=resourceProperties["BlueprintName"],
        type='DOCUMENT',
        blueprintStage=resourceProperties["blueprintStage"],
        schema=load_blueprint_schema(resourceProperties)
    )
    return response["blueprint"]

def on_create(event):
    """
    This function is called when a new resource is being created.
    It prints the resource properties, calls the create_or_update_index function
    to create or update the index, and returns the response from that function.
    """
    resourceProperties = event["ResourceProperties"]
    print("create new resource with props %s" % resourceProperties)
    blueprint = create_blueprint(resourceProperties=resourceProperties)

    return {
        'PhysicalResourceId': blueprint["blueprintArn"],
        "Data": {
            "blueprintArn": blueprint["blueprintArn"]
        }
    }

def on_update(event):
    """
    This function is called when an existing resource is being updated.
    It prints the resource properties, calls the create_or_update_index function
    to create or update the index, and returns the response from that function.
    """
    resourceProperties = event["ResourceProperties"]
    physical_resource_id = event["PhysicalResourceId"]
    print("update  resource with props %s" % resourceProperties)
    blueprint = update_blueprint(physical_resource_id, resourceProperties=resourceProperties)
    return {
        "PhysicalResourceId": blueprint["blueprintArn"], 
        "Data": {
            "blueprintArn": blueprint["blueprintArn"]
        }
    }
    

def on_delete(event):
    """
    This function is called when a resource is being deleted.
    It returns the physical resource ID of the resource being deleted.
    """
    physical_id = event["PhysicalResourceId"]
    delete_blueprint(event)
    return {'PhysicalResourceId': physical_id}

def is_complete(event, context):
    """
    This function checks if the resource is in a stable state based on the request type.
    It returns a dictionary indicating whether the resource is complete or not.
    """
    physical_id = event["PhysicalResourceId"]
    request_type = event["RequestType"]

    # check if resource is stable based on request_type
    # is_ready = ...

    return {'IsComplete': True}
