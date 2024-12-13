
from aws_cdk import (
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_s3_assets as s3_assets,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy,
    custom_resources,
    CustomResource,
    aws_lambda as _lambda
)
from constructs import Construct
from datetime import datetime, timezone
import os
from collections import namedtuple

class Database(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.database_name = self.node.try_get_context('database_name')

        self.database_cluster = self.create_database_cluster(self.database_name)

        schema_assets = self.create_schema_file_assets()
        manage_schema_lambda_function = self.create_manage_schema_lambda_function(
            cluster=self.database_cluster,
            create_schema_asset=schema_assets.create,
            delete_schema_asset=schema_assets.delete,
            database_name=self.database_name,
            update_schema_asset=schema_assets.update if schema_assets.update else None,
            initial_data_asset=schema_assets.initial_data if schema_assets.initial_data else None
        )
        self.create_create_schema_custom_resource(manage_schema_lambda_function)

        self.database_cluster.secret.grant_read(manage_schema_lambda_function)

        CfnOutput(self, "DatabaseName",
            value=self.database_name
        )

        CfnOutput(self, "DatabaseSecret",
            value=self.database_cluster.secret.secret_arn
        )
        
    def create_database_cluster(self, 
                                database_name:str):
        # Create VPC for the database
        vpc = ec2.Vpc(self, "AuroraVPC",
            max_azs=2,
        )

        # Create Aurora Serverless V2 Cluster
        cluster = rds.DatabaseCluster(self, "claims-review-cluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4
            ),
            serverless_v2_max_capacity=2,
            serverless_v2_min_capacity=0.5,
            writer=rds.ClusterInstance.serverless_v2("writer",
                publicly_accessible=True
            ),
            vpc=vpc,
            default_database_name=database_name,
            removal_policy=RemovalPolicy.DESTROY,
            enable_data_api=True
        )
        return cluster

    def create_create_schema_custom_resource(self, 
                                             manage_schema_lambda_function: _lambda.Function):
 
        # Create Custom Resource provider
        provider = custom_resources.Provider(
            self, 
            "manage_schema_provider",
            on_event_handler=manage_schema_lambda_function)

        # Create Custom Resource to execute schema
        manage_schema_custom_resource = CustomResource(
            self,
            "manage_aurora_schema",
            service_token=provider.service_token,
            properties={
                "timestamp": str(datetime.now(timezone.utc))  # Force update on each deployment
            }
        )
        manage_schema_custom_resource.node.add_dependency(self.database_cluster)
    
    def create_schema_file_assets(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Upload the SQL schema file to S3 as an asset
        create_schema_file = s3_assets.Asset(
            self,
            "CreateSQLSchemaAsset",
            path=os.path.join(current_dir, "schemas/create_database_schema.sql"),
        )
        update_schema_file = None
        #if update_database_schema.sql exists then create an S3 asset for it
        if os.path.exists(os.path.join(current_dir, "schemas/update_database_schema.sql")):
            update_schema_file = s3_assets.Asset(
                self,
                "UpdateSQLSchemaAsset",
                path=os.path.join(current_dir, "schemas/update_database_schema.sql"),
            )

        # Upload the SQL schema file to S3 as an asset
        delete_schema_file = s3_assets.Asset(
            self,
            "DeleteSQLSchemaAsset",
            path=os.path.join(current_dir, "schemas/delete_database_schema.sql"),
        )

        # Upload the SQL schema file to S3 as an asset
        initial_data_file = s3_assets.Asset(
            self,
            "InitialDataAsset",
            path=os.path.join(current_dir, "data/initial_data.sql"),
        )
        
        SchemaAssets = namedtuple('SchemaAssets', ['create', 'delete', 'update', 'initial_data'])  # import collections
        return SchemaAssets(create_schema_file, delete_schema_file, update_schema_file, initial_data_file)
    
    def create_manage_schema_lambda_function(self,
            cluster:rds.DatabaseCluster,
            database_name:str,
            create_schema_asset:s3_assets.Asset,
            delete_schema_asset:s3_assets.Asset,
            update_schema_asset:s3_assets.Asset=None,
            initial_data_asset:s3_assets.Asset=None
        ):
        
        # Define the Lambda function that will execute the schema
        manage_schema_lambda_function = _lambda.Function(
            self,
            "schema_executor",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/claims_review/manage_schema"),
            environment={
                "CLUSTER_ARN": cluster.cluster_arn,
                "SECRET_ARN": cluster.secret.secret_arn,
                "DATABASE_NAME": database_name,
                "CREATE_SCHEMA_FILE": create_schema_asset.s3_object_url,  # Path to the uploaded SQL file in S3
                "DELETE_SCHEMA_FILE": delete_schema_asset.s3_object_url,  # Path to the uploaded SQL file in S3
                **({'INITIAL_DATA_FILE': initial_data_asset.s3_object_url} if initial_data_asset is not None else {}),
                **({'UPDATE_SCHEMA_FILE': update_schema_asset.s3_object_url} if update_schema_asset is not None else {}),
            }
        )

        create_schema_asset.grant_read(manage_schema_lambda_function)
        delete_schema_asset.grant_read(manage_schema_lambda_function)
        if update_schema_asset:
            update_schema_asset.grant_read(manage_schema_lambda_function)
        if initial_data_asset:
            initial_data_asset.grant_read(manage_schema_lambda_function)

        cluster.secret.grant_read(manage_schema_lambda_function)
        cluster.grant_data_api_access(manage_schema_lambda_function)
        
        return manage_schema_lambda_function        