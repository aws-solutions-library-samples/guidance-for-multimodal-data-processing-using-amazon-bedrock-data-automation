from time import time
import json
import boto3
import os

s3 = boto3.client("s3")

session = boto3.Session()  
rds_data = session.client(
    service_name='rds-data'
)

CLAIMS_DB_CLUSTER_ARN = os.environ['CLAIMS_DB_CLUSTER_ARN']
CLAIMS_DB_DATABASE_NAME = os.environ['CLAIMS_DB_DATABASE_NAME']
CLAIMS_DB_CREDENTIALS_SECRET_ARN = os.environ['CLAIMS_DB_CREDENTIALS_SECRET_ARN']


MEMBER_DETAILS_QUERY = """
    SELECT insured_id,insured_name,insured_group_number,insured_plan_name,insured_birth_date,insured_policy_number,phone_number
,address FROM Insured_Person WHERE insured_policy_number=:insured_policy_number;
"""

PATIENT_DETAILS_QUERY = """
    SELECT p.patient_id,i.insured_id,p.patient_firstname,p.patient_lastname,p.patient_birth_date,p.relationship_to_insured,p.phone_number,p.sex,p.address 
    FROM Patient p, Insured_Person i WHERE i.insured_id = p.insured_id AND i.insured_policy_number = :insured_policy_number 
    AND patient_lastname=:patient_lastname AND patient_birth_date=TO_DATE(:patient_birth_date,'YYYY-MM-DD');
"""

MEMBER_AND_PATIENT_DETAILS_QUERY = """
    SELECT 
    i.insured_id,i.insured_name,i.insured_group_number,i.insured_plan_name,i.insured_birth_date,i.insured_policy_number,i.address insured_address,i.phone_number insured_phone_number,
    p.patient_id,p.patient_firstname,p.patient_lastname,p.patient_birth_date,p.relationship_to_insured,p.phone_number patient_phone_number,p.sex patient_sex,p.address patient_address
    FROM Patient p, Insured_Person i WHERE i.insured_id = p.insured_id AND i.insured_policy_number = :insured_policy_number 
    AND patient_lastname=:patient_lastname AND patient_birth_date=TO_DATE(:patient_birth_date,'YYYY-MM-DD');
"""

CREATE_CLAIM_QUERY = """
    INSERT INTO Claim (patient_id,claim_date,diagnosis_1,diagnosis_2,diagnosis_3,diagnosis_4,total_charges,balanceDue, amountPaid,claim_status) VALUES 
    (:patient_id, TO_DATE(:claim_date, 'YYYY-MM-DD'), :diagnosis_1, :diagnosis_2, :diagnosis_3, :diagnosis_4, :total_charges,:balanceDue, :amountPaid, :claim_status)
    RETURNING claim_id
"""
CREATE_SERVICE_QUERY = """
    INSERT INTO SERVICE (claim_id, date_of_service, place_of_service,type_of_service,procedure_code,procedure_code) VALUES 
    (:claim_id, TO_DATE(:date_of_service, 'YYYY-MM-DD'), :place_of_service, :type_of_service, :procedure_code, :procedure_code)
    RETURNING service_id
"""



class ParameterError(Exception):
    """Base exception for parameter-related errors"""
    pass

class MissingParametersError(ParameterError):
    """Raised when the parameters dict is empty or missing"""
    pass

class ParameterNotFoundError(ParameterError):
    """Raised when a specific parameter is not found"""
    pass


def run_command(sql_statement, parameters=None):
    print(f"SQL statement: {sql_statement}")
    result = rds_data.execute_statement(
        resourceArn=CLAIMS_DB_CLUSTER_ARN,
        secretArn=CLAIMS_DB_CREDENTIALS_SECRET_ARN,
        database=CLAIMS_DB_DATABASE_NAME,
        sql=sql_statement,
        includeResultMetadata=True,
        parameters=parameters
    )
    return result

def getClaimsFormData(event) :
    s3_uri = get_parameter(event, "s3URI")
    response = s3.get_object(Bucket=s3_uri.split('/',3)[2], Key=s3_uri.split('/',3)[3])
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)

    #create response json as a list of dictionaries
    response =  {
            "claims_form_data": json_content
    }
    return response


def getAllOpenClaims(event) :
    
    #create response json as a list of dictionaries
    response = [
        {
            "claimId": "11111111",
            "policyHolderId": "John Doe",
            "claimStatus": "2021-01-01",
        }
    ]
    return response

def get_parameter(event, parameter_name):
    params = event["parameters"]
    if not params:
        raise MissingParametersError("No parameters provided")
    else:
        param = [p for p in params if p["name"] == parameter_name]
        if not param:
            raise ParameterNotFoundError(f"Missing parameter: {parameter_name}")
        else:
            return param[0]["value"]

def get_request_property(event, property_name, defaultValue=None):
    request_body = event["requestBody"]
    content = request_body["content"]
    application_json = content["application/json"]
    properties = application_json["properties"]
    property = [p for p in properties if p["name"]==property_name]
    if not property:
        if not defaultValue:
            raise ParameterNotFoundError(f"Missing parameter: {property_name}")
        else:
            return defaultValue
    else:
        value = None
        match property[0]["type"]:
            case 'string':
                value = str(property[0]["value"])
            case 'number':
                value = float(property[0]["value"])
            case 'integer':
                value = int(property[0]["value"])
            case _:
                value = property[0]["value"]
    return value

def results_by_column_name(result):
    columns = [column["name"] for column in result["columnMetadata"]]
    records = result["records"]
    results = []
    for record in records:
        print(record)
        values = [list(value.values())[0] for value in record]
        print(values)
        results.append(dict(zip(columns, values)))
        print(results)
    return results

# Function to create parameter dict
def create_param(name, value):
    print(f"name:{name}, value:{value}")
    if value is None:
        return {'name': name, 'value': {'isNull': True}}
    elif isinstance(value, str):
        return {'name': name, 'value': {'stringValue': value}}
    elif isinstance(value, int):
        return {'name': name, 'value': {'longValue': value}}
    elif isinstance(value, float):
        return {'name': name, 'value': {'doubleValue': value}}
    elif isinstance(value, bool):
        return {'name': name, 'value': {'booleanValue': value}}
    else:
        raise ValueError(f"Unsupported type for {name}: {type(value)}")

def getMemberAndPatientDetails(event) :

    insured_policy_number = get_parameter(event, "insured_id_number")
    patient_lastname = get_parameter(event, "patient_last_name")
    patient_birth_date = get_parameter(event, "patient_birth_date")
    parameters=[
        {
            'name':'insured_policy_number', 
            'value':{'stringValue':insured_policy_number}
        },
        {
            'name':'patient_lastname', 
            'value':{'stringValue':patient_lastname}
        },
        {
            'name':'patient_birth_date', 
            'value':{'stringValue':patient_birth_date}
        }
    ] 

    result = run_command(MEMBER_AND_PATIENT_DETAILS_QUERY, parameters)
    print(result)
    data = results_by_column_name(result)
    if not data:
        return f"""
            Unable to get Member and/or Patient details with 
            Insured Id Number={insured_policy_number},
            Patient Last Name={patient_lastname},
            Patient Birth Date={patient_birth_date}
        """
    member = data[0]
    response = {
        "insuredId": member['insured_id'],
        "memberName": member['insured_name'],
        "memberAddress": member['insured_address'],
        "memberDateOfBirth": member['insured_birth_date'],
        "memberPlanDetails": {
            "memberGroupNumber": member['insured_group_number'],
            "memberPlanName": member['insured_plan_name'],
            "memberPlanNumber": member['insured_policy_number'],
        },
        "memberPhoneNumber": member['insured_phone_number'],
        "patientId": member['patient_id'],
        "patientFirstName": member['patient_firstname'],
        "patientLastName":  member['patient_lastname'],
        "patientDateOfBirth": member['patient_birth_date'],
        "patientRelationshipToInsured": member['relationship_to_insured'],
        "patientPhoneNumber": member['patient_phone_number'],
        "patientSex": member['patient_sex'],
        "patientAddress": member['patient_address'],
    }

    return response

def getMemberDetails(event) :

    insured_policy_number = get_parameter(event, "insured_id_number")
    parameters=[
        {
            'name':'insured_policy_number', 
            'value':{'stringValue':insured_policy_number}
        }
    ] 

    result = run_command(MEMBER_DETAILS_QUERY, parameters)
    print(result)
    data = results_by_column_name(result)
    if not data:
        return f"Insured Member with last name {insured_policy_number}  not found"
    member = data[0]
    response = {"memberName": member['insured_name'],
                "memberAddress": member['address'],
                "memberDateOfBirth": member['insured_birth_date'],
                "memberPlanDetails": {
                    "memberGroupNumber": member['insured_group_number'],
                    "memberPlanName": member['insured_plan_name'],
                    "memberPlanNumber": member['insured_policy_number'],
                },
                "memberPhoneNumber": member['phone_number']
              }

    return response

def listClaimsForInsured(event) :
    response = [
        {
            "claimId": "XXXXXXXX",
            "policyHolderId": "John Doe",
            "claimStatus": "2021-01-01",
        }
    ]
    return response

def getClaim(event):
    response = {"claimId": "XXXXXXXX",
                "claim_description": "Not Implement"
    }

    return response

def create_claim(event) :
    parameters = [
        create_param("patient_id", get_request_property (event, "patient_id")),
        create_param("claim_date", get_request_property(event,"claim_date")),
        create_param("diagnosis_1", get_request_property(event,"diagnosis_1")),
        create_param("diagnosis_2", get_request_property(event,"diagnosis_2",'')),
        create_param("diagnosis_3", get_request_property(event,"diagnosis_3",'')),
        create_param("diagnosis_4", get_request_property(event,"diagnosis_4",'')),
        create_param("total_charges", get_request_property(event,"total_charges")),
        create_param("amountPaid", get_request_property(event,"amount_paid")),
        create_param("balanceDue", get_request_property(event,"balance")),
        create_param("claim_status", get_request_property(event,"claim_status","NEW"))
    ]
    print(parameters)
    result = run_command(sql_statement=CREATE_CLAIM_QUERY, parameters=parameters)
    
    print(result)
    data = results_by_column_name(result)
    if not data:
        raise ParameterNotFoundError(f"Missing return record after Insert")
    response = {
        "claim_id": data[0]["claim_id"]
    }
    return response

def create_claim_service(event):
    claim_id = get_parameter(event, "claim_id")
    response = {
        "claimId": claim_id,
        "claim_description": "Not Implemented"}
    services_text = get_request_property(event,"services")
    services = json.loads(services_text)
    print(services)
    for service in services: # type: ignore
        parameters = [
            create_param("date_of_service", get_request_property(event,"date_of_service")),
            create_param("place_of_service", get_request_property(event,"place_of_service")),
            create_param("type_of_service", get_request_property(event,"type_of_service")),
            create_param("procedure_code", get_request_property(event,"procedure_code")),
            create_param("amount", get_request_property(event,"charge_amount"))
        ]
        result = run_command(sql_statement=CREATE_SERVICE_QUERY, parameters=parameters)

    return response


def getPatient(event):

    patient_lastname = get_parameter(event, "patient_lastName")
    patient_birth_date = get_parameter(event, "patient_birth_date")
    insured_policy_number = get_parameter(event, "insured_id_number")
    parameters=[
        {
            'name':'patient_lastname', 
            'value':{'stringValue':patient_lastname}
        },
        {
            'name':'insured_policy_number', 
            'value':{'stringValue':insured_policy_number}
        },
        {
            'name':'patient_birth_date', 
            'value':{'stringValue':patient_birth_date}
        }
    ] 

    result = run_command(PATIENT_DETAILS_QUERY, parameters)
    print(result)
    data = results_by_column_name(result)
    if not data:
        return f"Patient with last name {patient_lastname} and birth data {patient_birth_date} not found associated with insured id number {insured_id_number}"
    patient = data[0]
    response = {
        "firstName": patient['patient_firstname'],
        "lastName": patient['patient_lastname'],
        "dateOfBirth": patient['patient_birth_date'],
        "gender": patient['sex'],
        "address": patient['address'],
        "relationshipToInsured": patient['relationship_to_insured'],
        "phoneNumber": patient['phone_number']
    }

    return response

def createPatient(event) :
    CREATE_CLAIM_QUERY.format(claim_values=get_parameter(event, "claim_values"))
    response = {"claimId": "XXXXXXXX"}
    return response


def lambda_handler(event, context):
    print(event)
    action = event["actionGroup"]
    api_path = event["apiPath"]
    httpMethod = event["httpMethod"]
    response_code = 200
    response = None
    try:
        match api_path:
            case '/member_and_patient':
                response = getMemberAndPatientDetails(event)
            case '/member/{insured_id_number}':
                response = getMemberDetails(event)
            case '/claims' :
                if(httpMethod == "GET"):
                    response = getAllOpenClaims(event)
                elif(httpMethod == "POST"):
                    response = create_claim(event)
            case '/patient' :
                if(httpMethod == "GET"):
                    response = getPatient(event)
                elif(httpMethod == "POST"):
                    response = createPatient(event)
            case '/get_claims_form_data':
                response = getClaimsFormData(event)
            case '/claims/{claim_id}':
                response = getClaim(event)
            case '/claims/insured/{insuredId}':
                response = listClaimsForInsured(event)
            case 'claims/{claim_id}/service':
                response = create_claim_service(event)
            case _:
                response_code = 404
                response = {"error": f"{action}::{api_path} is not a valid API, try another one."}
    except ParameterError as pe:
        response_code = 400
        response = {"error": str(pe)}
    except Exception as e:
        response_code = 500
        response = {"error": str(e)}


    response_body = {"application/json": {"body": json.dumps(response)}}


    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    session_attributes = event["sessionAttributes"]
    prompt_session_attributes = event["promptSessionAttributes"]

    api_response = {
        "messageVersion": "1.0",
        "response": action_response,
        "sessionAttributes": session_attributes,
        "promptSessionAttributes": prompt_session_attributes,
    }
    print(api_response)
    return api_response 