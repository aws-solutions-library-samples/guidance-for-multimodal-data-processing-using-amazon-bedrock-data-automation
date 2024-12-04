from aws_cdk import (
    CfnOutput,
    aws_iam as iam,
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    Duration,
    custom_resources,
    CustomResource
)
from typing import Optional

from constructs import Construct

class DocumentAutomation(Construct):
    def __init__(self, scope: Construct, construct_id: str,
                    claims_review_agent_id: str,
                    claims_review_agent_alias_id:str,
                    claims_review_agent_arn:str,
                    claims_review_agent_alias_arn:str,
                    **kwargs) -> None:

        super().__init__(scope, construct_id, **kwargs)
        data_project_arn = self.node.try_get_context("data_project_arn")
        #blueprint_arn = self.node.try_get_context("blueprint_arn")
        blueprint_name= self.node.try_get_context("blueprint_name")

        bda_runtime_endpoint = self.node.try_get_context("bda_runtime_endpoint")
        bda_endpoint = self.node.try_get_context("bda_endpoint")

        blueprint_creation_custom_resource = self.create_blueprint_creation_lambda_function(
             bda_endpoint=bda_endpoint,
            blueprint_name=blueprint_name)
        blueprint_arn = blueprint_creation_custom_resource.get_att_string("blueprintArn")
        # Bucket to store claim form submissions
        claims_submission_bucket = self.create_claims_submission_bucket()
        
        # Bucket to store data insights from claim forms
        self.claims_review_bucket = self.create_claims_review_bucket()

        # Lambda function to trigger bedrock data insight on submitted claim forms
        invoke_data_automation_lambda_function = self.create_invoke_data_automation_function(
            self.claims_review_bucket, 
            **({'blueprint_arn': blueprint_arn} if blueprint_arn is not None else {}),
            **({'bda_endpoint': bda_runtime_endpoint} if bda_runtime_endpoint is not None else {}),
            **({'data_project_arn': data_project_arn} if data_project_arn is not None else {})
        )
        
        # Grant the Lambda function permission to access the S3 bucket.
        claims_submission_bucket.grant_read(invoke_data_automation_lambda_function)
        self.claims_review_bucket.grant_read_write(invoke_data_automation_lambda_function)

        # EventBridge Rule to trigger Bedrock Data Insight when a new Claim form is submitted
        self.create_eventbridge_rule_to_invoke_document_automation(claims_submission_bucket=claims_submission_bucket,
                                                            invoke_data_automation_lambda_function=invoke_data_automation_lambda_function)

        # EventBridge Rule to trigger Bedrock Agent when a new Claim form is successfully processed by Bedrock Data Insight
        claims_verification_lambda_function = self.create_invoke_claims_verification_function(
                    claims_review_agent_id=claims_review_agent_id,
                    claims_review_agent_arn=claims_review_agent_arn,
                    claims_review_agent_alias_id=claims_review_agent_alias_id,
                    claims_review_agent_alias_arn=claims_review_agent_alias_arn
                )
        self.claims_review_bucket.grant_read_write(claims_verification_lambda_function)
        self.create_eventbridge_rule_to_invoke_claims_verification(
             claims_verification_lambda_function=claims_verification_lambda_function)
        
    def create_blueprint_creation_lambda_function(self, 
                                                  bda_endpoint:str,
                                                  blueprint_name:str):
         
        ######################################
        #Temp layer. shouldn't need after boto3-bda-ga
        
        # Create layer
        layer = _lambda.LayerVersion(self, 'blueprint_creation_lambda_layer',
            description='Dependencies for the Blueprint creation lambda function',
            code= _lambda.Code.from_asset( 'lambda/claims_review/layer/'), # required
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_10
            ],
        )
        ######################################

        blueprint_creation_lambda_function = _lambda.Function(
            self, 'blueprint-creation',
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset('lambda/claims_review/blueprint_creation'),
            handler='index.on_event',
            timeout=Duration.seconds(300),
            layers=[layer],
            environment={
                 **({'ENDPOINT': bda_endpoint} if bda_endpoint is not None else {}),
                'BLUEPRINT_NAME':blueprint_name
            }
        )

        blueprint_creation_lambda_function.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:ListBlueprints", "bedrock:GetBlueprint"],
            resources=[
                 f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:blueprint/*"
            ]
        ))

        #Create the Custom Resource Provider backed by Lambda Function
        claims_review_blueprint_creation_provider = custom_resources.Provider(
            self, 'claims_review_blueprint_creation_provider',
            on_event_handler=blueprint_creation_lambda_function,
            provider_function_name="claims-review_blueprint_creation_provider"
        )
        blueprint_creation_custom_resource = CustomResource (
            self, f"claims_review_blueprint_creation_custom_resource",
            service_token=claims_review_blueprint_creation_provider.service_token,
        )

        return blueprint_creation_custom_resource

    def claims_submission_bucket(self):
        claims_submission_bucket_name = self.node.try_get_context("claims_submission_bucket_name")
        bucket = s3.Bucket(self,"claims-submission-bucket",
            #bucket_name=f"{claims_submission_bucket_name}-{str(uuid.uuid4())}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            event_bridge_enabled=True
        )   
        CfnOutput(self, "output_claims_submission_bucket",
            export_name=f"{claims_submission_bucket_name}-bucket",
            value=bucket.bucket_name)

        return bucket
    
    def create_claims_review_bucket(self):
        claims_review_bucket_name = self.node.try_get_context("claims_review_bucket_name")
        bucket = s3.Bucket(self,
            "claims_review_bucket",
            #bucket_name=f"{claims_review_bucket_name}-{str(uuid.uuid4())}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            event_bridge_enabled=True
    )   
        CfnOutput(self, "output_claims_review_bucket",
            export_name=f"{claims_review_bucket_name}-bucket",
            value=bucket.bucket_name)
        
        return bucket

    def create_invoke_data_automation_function(self,
                                                   claims_review_bucket: s3.Bucket,
                                                   blueprint_arn: Optional[str]=None,
                                                   data_project_arn: Optional[str]=None,
                                                   bda_endpoint: Optional[str]=None):
         
        
        if not any((blueprint_arn, data_project_arn)):
            raise ValueError("At least one of data_project_arn or blueprint_arn must be provided")
        
        ######################################
        #Temp layer. shouldn't need after boto3-bda-ga
        
        # Create layer
        layer = _lambda.LayerVersion(self, 'invoke_data_automation_lambda_layer',
            description='Dependencies for the document automation lambda function',
            code= _lambda.Code.from_asset( 'lambda/claims_review/layer/'), # required
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_10
            ],
        )
        ######################################

        document_automation_lambda_function = _lambda.Function(
            self, 'invoke_data_automation',
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset('lambda/claims_review/invoke_data_automation'),
            handler='index.lambda_handler',
            timeout=Duration.seconds(300),
            layers=[layer],
            environment={k:v for k,v in {
                'CLAIMS_REVIEW_BUCKET_NAME': claims_review_bucket.bucket_name,
                'ENDPOINT':bda_endpoint,
                'DATA_PROJECT_ARN':data_project_arn,
                'BLUEPRINT_ARN':blueprint_arn
            }.items() if v is not None}
        )
        
        resources = [resource for resource in [blueprint_arn, data_project_arn] if resource is not None]
        #TODO: Update policy after BDA SDK is available
        document_automation_lambda_function.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeDataAutomationAsync"],
            resources=resources
        ))

        return document_automation_lambda_function

    def create_invoke_claims_verification_function(self, 
                            claims_review_agent_id:str, 
                            claims_review_agent_arn:str,
                            claims_review_agent_alias_id:str,
                            claims_review_agent_alias_arn:str):
        
        claims_verification_lambda_function = _lambda.Function(
            self, 'invoke_verification',
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset('lambda/claims_review/invoke_verification'),
            handler='index.lambda_handler',
            timeout=Duration.seconds(300),
            environment={
                'CLAIMS_REVIEW_AGENT_ID': claims_review_agent_id,
                'CLAIMS_REVIEW_AGENT_ALIAS_ID': claims_review_agent_alias_id
            }
        )

        #TODO: Update policy after BDA SDK is available
        claims_verification_lambda_function.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeAgent"],
            resources=[claims_review_agent_arn, claims_review_agent_alias_arn]
        ))

        return claims_verification_lambda_function

    def create_eventbridge_rule_to_invoke_document_automation(self,
                                                       claims_submission_bucket: s3.Bucket,
                                                       invoke_data_automation_lambda_function: _lambda.Function):
        # Create an EventBridge rule.
            document_automation_rule = events.Rule(self, "on_claim_submission",
                event_pattern=events.EventPattern(
                    source=["aws.s3"],
                    detail_type=["Object Created", "Object Updated"],
                    detail={
                        "bucket": {
                            "name": [claims_submission_bucket.bucket_name]
                        }
                    }
                )
            ) 

            # Add a target to the rule.
            document_automation_rule.add_target(
                targets.LambdaFunction(
                    handler=invoke_data_automation_lambda_function,
                    max_event_age=Duration.hours(2),
                    retry_attempts=2
                ) # type: ignore
            )

    def create_eventbridge_rule_to_invoke_claims_verification(self,
                        claims_verification_lambda_function: _lambda.Function):
        # Create an EventBridge rule.
            claim_review_trigger_rule = events.Rule(self, "data_automation_completed",
                event_pattern=events.EventPattern(
                    source= ["aws.bedrock-data-insights", "aws.bedrock-data-insights-test"],
                    detail_type=["Insights Extraction Job Completed"]
                )
            )

            # Add a target to the rule.
            claim_review_trigger_rule.add_target(
                targets.LambdaFunction(
                    handler=claims_verification_lambda_function,
                    max_event_age=Duration.hours(2),
                    retry_attempts=2
                )
            )
