import os
from aws_cdk import (
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as _lambda,
    Duration,
    Stack,
    CustomResource,
    CfnOutput,
    CfnParameter
)

import json
from constructs import Construct
from .prompts.claims_review_agent import claims_review_agent_instruction
from stacks.claims_review_stack.vector_store import VectorStore
from stacks.claims_review_stack.knowledge_base import KnowledgeBase
from stacks.claims_review_stack.document_automation import DocumentAutomation
from .prompts.prompt_overrides import prompt_overrides
from stacks.claims_review_stack.database import Database
class ClaimsReviewAgentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None: 
        super().__init__(scope, construct_id, **kwargs)

        foundation_model_id = CfnParameter(
            self,
            "FoundationModelId",
            type="String",
            description="The foundation model id to use for the agent",
            default=None
        )

        aurora_serverless_v2 = Database(self,"auroraV2")
        database_cluster = aurora_serverless_v2.database_cluster
        bedrock_service_role = self.create_bedrock_service_role (
                                           service_role_name = "ClaimsEoCKnowledgeBaseServiceRole")

        claims_review_agent_actions_role = self.create_claims_review_agent_actions_role()
        database_cluster.grant_data_api_access(claims_review_agent_actions_role)
        vector_store =  self.create_vector_store(
            bedrock_service_role = bedrock_service_role
        )

        datasource_sync_lambda_function = self.create_datasource_sync_lambda_function()

        knowledge_bases = self.create_knowledge_bases(
            bedrock_service_role=bedrock_service_role,
            vector_store=vector_store,
            datasource_sync_lambda_function=datasource_sync_lambda_function
        )

        claims_review_agent_actions_lambda_function = self.create_claims_review_agent_actions_lambda_function(
            claims_review_agent_actions_role=claims_review_agent_actions_role,
            database_cluster_arn=database_cluster.cluster_arn,
            database_credentials_secret=database_cluster.secret.secret_arn,
            default_database_name=aurora_serverless_v2.database_name
        )
        claims_review_agent = self.create_agent(
            claims_review_agent_actions_lambda_function=claims_review_agent_actions_lambda_function,
            claims_review_action_group_schema=self.get_claims_review_action_group_schema(),
            foundation_model_id = foundation_model_id.value_as_string,
            knowledge_bases=knowledge_bases) 
        claims_review_agent_alias = self.create_claims_review_agent_alias(claims_review_agent=claims_review_agent)

        document_automation = self.create_document_automation(
            claims_review_agent_id=claims_review_agent.attr_agent_id,
            claims_review_agent_arn = claims_review_agent.attr_agent_arn,
            claims_review_agent_alias_id=claims_review_agent_alias.attr_agent_alias_id,
            claims_review_agent_alias_arn=claims_review_agent_alias.attr_agent_alias_arn
        )
        
        document_automation.claims_review_bucket.grant_read(claims_review_agent_actions_role)

        self.output_kb_info(
            agent_alias_id=claims_review_agent_alias.attr_agent_alias_id,
            agent_id=claims_review_agent.attr_agent_id
        )   

    def create_claims_review_agent_actions_role(self):
        return iam.Role(self, "claims_review_agent_actions_role",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com", conditions={"StringEquals": {"aws:SourceAccount": self.account}}),
        description="Role for the Action Group functions for the Claims Review Agent",
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        ]
    )

    def create_claims_review_agent_actions_lambda_function(self,
                    claims_review_agent_actions_role: iam.Role,
                    database_cluster_arn:str,
                    database_credentials_secret:str,
                    default_database_name:str) ->_lambda.Function:
                        
        #create a lambda layer from the functions/layer directory
        claims_review_agent_actions_layer = _lambda.LayerVersion(self, 'claims_review_agent_actions_layer',
            code=_lambda.Code.from_asset('lambda/claims_review/layer'),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_10]
        )

        claims_review_agent_actions_function = _lambda.Function(
            self, 'agent_actions',
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset('lambda/claims_review/claims_review_agent_actions'),
            handler='index.lambda_handler',
            timeout=Duration.seconds(600),
            role=iam.Role.from_role_arn(self, "LambdaRole", claims_review_agent_actions_role.role_arn),
            layers=[claims_review_agent_actions_layer],
            environment={
                "CLAIMS_DB_CLUSTER_ARN": database_cluster_arn,
                "CLAIMS_DB_CREDENTIALS_SECRET_ARN": database_credentials_secret,
                "CLAIMS_DB_DATABASE_NAME": default_database_name
            }
        )
        return claims_review_agent_actions_function
        
    
    def create_bedrock_agent_resource_role(self,
                                           claims_review_agent_resource_role_name: str,
                                           knowledge_bases: list[bedrock.CfnKnowledgeBase],
                                           foundation_model_id: str) -> iam.Role:
        
        #Create a resource role for our Claims Review Bedrock Agent
        claims_review_agent_resource_role = iam.Role(self, "claims_review_agent_resource_role",
            description="Agent Resource Role for the Claims Review Bedrock Agent",
            role_name=claims_review_agent_resource_role_name,
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com", conditions={"StringEquals": {"aws:SourceAccount": self.account}})
        )

        #add policy to allow model access
        claims_review_agent_resource_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/{foundation_model_id}"
                ]
            )
        )
        claims_review_agent_resource_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Retrieve"
                ],
                resources= [knowledgebase.attr_knowledge_base_arn for knowledgebase in knowledge_bases]
            )
        )
        return claims_review_agent_resource_role
    def get_claims_review_action_group_schema(self):
                # Construct the path to the schema file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, "schemas", "claims_review_openapi.json")
        # Open the file using the constructed path

        with open(schema_path, "r") as f:
            claims_review_action_group_schema = json.load(f)
            return claims_review_action_group_schema

    def create_agent(self,
                    claims_review_agent_actions_lambda_function: _lambda.Function,
                    claims_review_action_group_schema,
                    foundation_model_id,
                    knowledge_bases: list[bedrock.CfnKnowledgeBase]) -> bedrock.CfnAgent:
        # Get the current directory of the script
        agent_parameters = self.node.try_get_context('agent')

        claims_review_agent_resource_role = self.create_bedrock_agent_resource_role(
            claims_review_agent_resource_role_name = agent_parameters["claims_review_agent_resource_role_name"],
            knowledge_bases = knowledge_bases,
            foundation_model_id = foundation_model_id
        )
        
        prompt_override_configuration = prompt_overrides.get(foundation_model_id,None)
        claims_review_agent = bedrock.CfnAgent(self, "claims_review_agent",
            agent_name="claims-review-agent",
            # the properties below are optional
            action_groups=[bedrock.CfnAgent.AgentActionGroupProperty(
                action_group_name="claim_review_action_group",

                # the properties below are optional
                action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                    lambda_= claims_review_agent_actions_lambda_function.function_arn
                ),
                api_schema=bedrock.CfnAgent.APISchemaProperty(
                    payload=json.dumps(claims_review_action_group_schema)
                ),
                description="Claims Review Agent to verify customer claims, identify pending documents and send reminders to customer to submit pending documents",
            )],
            knowledge_bases=self.get_agent_knowledge_bases(knowledge_bases),
            agent_resource_role_arn=claims_review_agent_resource_role.role_arn,
            auto_prepare=True,
            description="Claims Review Agent",
            foundation_model=foundation_model_id,
            instruction=claims_review_agent_instruction,            
            tags={
                "project": "claims-review"
            },
            **({'prompt_override_configuration': prompt_override_configuration}if prompt_override_configuration is not None else {})
        )
        claims_review_agent_actions_lambda_function.grant_invoke(claims_review_agent_resource_role)
        claims_review_agent_actions_lambda_function.add_permission(
            "AllowBedrockInvocation",
            principal=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.account},
                    "ArnLike": {
                        "aws:SourceArn": claims_review_agent.attr_agent_arn
                    },
                }
            ),
            action="lambda:InvokeFunction",
        )
        return claims_review_agent

    def create_claims_review_agent_alias(self,
                                         claims_review_agent:bedrock.CfnAgent) -> bedrock.CfnAgentAlias:
        claims_review_agent_alias = bedrock.CfnAgentAlias(
            self,
            "claims_review_agent_alias",
            agent_id=claims_review_agent.attr_agent_id,
            agent_alias_name="live",
            # Description updates anytime the Agent resource is updated,
            # so that this Alias prepares a new version of the Agent when
            # the Agent changes
            description="Tracking agent timestamp " + claims_review_agent.attr_prepared_at,
        )
        claims_review_agent_alias.add_dependency(claims_review_agent)
        return claims_review_agent_alias

    def create_bedrock_service_role(self,
                            service_role_name: str ) -> iam.Role:
        return iam.Role(self, "kb_service_role",
            role_name=service_role_name, 
            inline_policies={
                "S3DataSourceAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject","s3:ListBucket"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {
                                    "aws:PrincipalAccount": Stack.of(self).account
                                }
                            }
                        )
                    ]
                ),
                "EmbeddingModelAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeModel"],
                            resources=[f"arn:aws:bedrock:{Stack.of(self).region}::foundation-model/*"]
                        )
                    ]
                ),
                "OpenSearchServerlessAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["aoss:APIAccessAll"],
                            resources=[f"arn:aws:aoss:{Stack.of(self).region}:{Stack.of(self).account}:collection/*"]
                        )
                    ]
                )
            },
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": Stack.of(self).account
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/*"
                    }
                }
            )
        )
    
    def create_vector_store(self, 
                        bedrock_service_role: iam.Role) -> VectorStore:

        vector_store_configuration = self.node.try_get_context('vector_store')
        claims_vector_store_collection_name = vector_store_configuration['collection_name']
        claims_vector_store_collection_description = vector_store_configuration['collection_description']

        return VectorStore(self, "vector_store",
                                kb_service_role_arn=bedrock_service_role.role_arn,
                                vector_store_collection_name=claims_vector_store_collection_name,
                                vector_store_collection_description=claims_vector_store_collection_description)

    def create_knowledge_bases(self,
                              vector_store: VectorStore,
                              bedrock_service_role: iam.Role,
                              datasource_sync_lambda_function: _lambda.Function) -> list:

        knowledge_bases_config = self.node.try_get_context('knowledge_bases')
        knowledge_bases = []
        for knowledge_base_name, knowledgebase_parameters in knowledge_bases_config.items():

            vector_store_index_creation_resource = self.create_vector_store_index(
                            service_token = vector_store.vector_store_index_creation_provider.service_token,
                            vector_store_index_name = knowledgebase_parameters["vector_store_index_params"]["index_name"],
                            aoss_collection_endpoint = vector_store.aoss_collection_endpoint
            )

            knowledge_base = KnowledgeBase(self,
                knowledge_base_name,
                kb_service_role_arn = bedrock_service_role.role_arn,
                vector_store_collection_arn = vector_store.aoss_collection_arn,
                knowledgebase_parameters = knowledgebase_parameters,
                datasource_sync_lambda_function = datasource_sync_lambda_function
            )
            knowledge_base.knowledgebase.add_dependency(vector_store_index_creation_resource.node.default_child)
            knowledge_bases.append(knowledge_base.knowledgebase)

        return knowledge_bases
    
    def create_vector_store_index(self,
                              service_token,
                              vector_store_index_name,
                              aoss_collection_endpoint
                              ) -> CustomResource:
        return  CustomResource (
            self, f"vector_store_index_creation_resource_{vector_store_index_name}",
            service_token=service_token,
            properties={
                "AOSSIndexName": vector_store_index_name,
                "AOSSHost": aoss_collection_endpoint
            }
        )
    
    def get_agent_knowledge_bases(self,knowledge_bases: list) -> list:
        agent_knowledge_bases = []
        for knowledge_base in knowledge_bases:
            agent_knowledge_bases.append(
                    bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    knowledge_base_id=knowledge_base.attr_knowledge_base_id,
                    description=knowledge_base.description,
                    knowledge_base_state="ENABLED"
                )
            )
        return agent_knowledge_bases
    
    def create_datasource_sync_lambda_function(self) -> _lambda.Function:

        return  _lambda.Function(
            self,
            "datasource_sync",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="index.lambda_handler",
            code=_lambda.Code.from_asset('lambda/claims_review/datasource_sync'),
            timeout=Duration.minutes(5)
        )

    def create_document_automation(self, 
                        claims_review_agent_id: str,
                        claims_review_agent_alias_id: str,
                        claims_review_agent_arn: str,
                        claims_review_agent_alias_arn: str
                    ):
        return DocumentAutomation(
            self,
            f"bda",
            claims_review_agent_id=claims_review_agent_id,
            claims_review_agent_arn=claims_review_agent_arn,
            claims_review_agent_alias_id=claims_review_agent_alias_id,
            claims_review_agent_alias_arn=claims_review_agent_alias_arn
        )
    
    def output_kb_info(self, 
                       agent_alias_id:str,
                       agent_id: str):
        
        CfnOutput(self, f"claims_review_agent_id",
                  value=agent_id,
                  description=f"Claims Review Agent Id",
                  export_name=f"claims-review-agent-id"
        )
        CfnOutput(self, f"claims_review_agent_alias_id",
                  value=agent_id,
                  description=f"Claims Review Agent Alias Id",
                  export_name=f"claims-review-agent-alias-id"
        )