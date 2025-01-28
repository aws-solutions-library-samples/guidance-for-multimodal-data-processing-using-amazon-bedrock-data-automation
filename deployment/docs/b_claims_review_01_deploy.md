# Claims Review Bedrock Agent Stack Documentation

## Overview

The `claims-review` is an AWS CDK stack that sets up an Amazon Bedrock agentic architecture to automate the processing and review of medical insurance claim forms using Amazon Bedrock Data Automation.


## Prerequisites

- Python 3.10 or higher
- AWS CLI configured with appropriate credentials
- Node.js and npm (for AWS CDK CLI)
- AWS CDK CLI installed (`npm install -g aws-cdk`)


## Select a Foundation Model to use with Bedrock Agent. 
Before deploying the stack, you need to choose a foundation model (FM) that the agent invokes to interpret user input and subsequent prompts in its orchestration process. The agent also invokes the FM to generate responses and follow-up steps in its process. The following sections provide information on selecting a foundation model and enabling access to the model.

For more details see [How Amazon Bedrock Agents works](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-how.html).


### Choosing a Model or an Inference Profile

**When choosing a model please follow the model provider acceptable end user policy**

#### Model Support By Feature and By Region

- Foundation models differ in the Amazon Bedrock features that they support. See [Model support by feature](https://docs.aws.amazon.com/bedrock/latest/userguide/models-features.html) 

- Amazon Bedrock foundation models differ in their regional support. See [Model support by AWS Region in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)

 > [!Note] Some models are accessible in some Regions only through cross-region inference. To learn more about cross-region inference, see [Increase throughput with cross-region
 >inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) and [Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html).

#### Access Amazon Bedrock foundation models
Before you can use a foundation model in Amazon Bedrock, you must request access to it. 
* See [Add or remove access to Amazon Bedrock foundation model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html)
* If choosing one of [Amazon Titan Text models](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-text-models.html) ensure the model **Supported use cases** include _Agents Support_

#### Using Inference Profiles
You can use a cross region inference profile in place of a foundation model to route requests to multiple Regions. When using inference profiles, make sure you've requested access to the models and the regions defined in the inference profiles that you want to use. For example, to gain access to make calls to the US Anthropic Claude 3 Haiku inference profile from the US West (Oregon) Region, do the following:

  1. Sign into the AWS Management Console in the US East (N. Virginia) Region and request model access to Anthropic Claude 3 Haiku by following the steps at Access Amazon  Bedrock foundation models.
  2. Change to the US West (Oregon) Region and request model access to Anthropic Claude 3 Haiku. 

> [!Important]
>Take a note of the foundation model id or the inference profile id. You would need to use the model id with the [`cdk deploy command`](#deploy-the-stack)

## Deployment Steps

> [!Note]
>If you’re continuing this part from Installation part 1, you can skip step 1-4

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:

   ```
   git clone https://github.com/aws-solutions-library-samples/guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation.git

   ```

2. Change to the `deployment` directory for the guidance repository <a name='deployment-directory'></a>


   ```
   cd guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation/deployment

   ```
3. Create and activate a virtual environment:  <a name='create_venv'></a>

   ```
   python -m venv .venv
   source .venv/bin/activate

   ```

4. Install required dependencies:
   ```
   pip install -r requirements.txt

   ```
5. Bootstrap AWS CDK (first-time only):
   
> [!Note]
> You would need a model id or an inference profile id for this step. See [Select a Foundation Model](#select-a-foundation-model-to-use-with-bedrock-agent)

   Using a foundation model 
   ```bash
   cdk bootstrap --context foundation_model_id=<<your_chosen_model_id>>
   ```
   
   Using an inference profile 
   ```bash
   cdk bootstrap  --context inference_profile_id=<<your_chosen_inference_profile_id>>
   ```
> [!Important]
> You must provide one of foundation model id or inference profile id, but not both


6. Go to the `layer` directory and install lambda layer dependencies into the `python` subdirectory:
   
   ```
   cd lambda/claims_review/layer/
   pip install -r requirements.txt --target python
   cd ../../..

   ```
  
7. Deploy the stack: <a name="deploy-the-stack"></a>

> [!Note]
> You would need a model id or an inference profile id for this step. See [Select a Foundation Model](#select-a-foundation-model-to-use-with-bedrock-agent)

   Using a foundation model 
   ```bash
   cdk deploy claims-review  --context foundation_model_id=<<your_chosen_model_id>>
   ```
   
   Using an inference profile 
   ```bash
   cdk deploy claims-review  --context inference_profile_id=<<your_chosen_inference_profile_id>>
   ```
> [!Important]
> You must provide one of foundation model id or inference profile id, but not both



   To protect you against unintended changes that affect your security posture, the CDK CLI prompts you to approve security-related changes before deploying them. When prompted, review the changes and Enter `y` for  `Do you wish to deploy these changes (y/n)?` if you intend to proceed.

   Alternatively, in one command

   Using a foundation model 
   ```bash
   cdk deploy claims-review  --context foundation_model_id=<<your_chosen_model_id>> --require-approval never 
   ```
   
   Using an inference profile 
   ```bash
   cdk deploy claims-review  --context inference_profile_id=<<your_chosen_inference_profile_id>> --require-approval never 
   ```

8. Wait for the stack deploy to complete. This may take a few minutes.


## Deployment Validation
To validate that your AWS CloudFormation stack
1. Log in to your personal AWS account in the AWS Console.
2. Navigate to the to the `AWS CloudFormation` Console by searching for AWS CloudFormation in the search bar at the top of the AWS Console page and Click on `CloudFormation` in the results.
3. From the `AWS CloudFormation` in the `Stacks` list, look for a stack with Stack name `claims-review`. Validate that the status shows 'CREATE_COMPLETE'

![Stack_create_complete][screenshot_stack_create_complete]

Alternatively, you can use the AWS CLI

  Check the stack status using the AWS CloudFormation service
   
   ```
    aws cloudformation describe-stacks --stack-name claims-review --query 'Stacks[0].StackStatus' --output text

   ```

  A successful initial deployment should show a <span style="color: green;">CREATE_COMPLETE</span> status and a successful subsequent deployment should show
  <span style="color: green;">UPDATE_COMPLETE</span> status


## Running the Guidance
See the guide [here](./b_claims_review_02_run_flow.md) for steps to run the claims review application
### 

## Security

The stack enforces the following security measures:

- The Bedrock Agent's Resource Role has the minimum permissions required to access the Foundation Model and invoke the Lambda function.
- The Lambda function's execution role has the basic execution permissions.
- The Lambda function is granted permission to be invoked by the Bedrock Agent.

## Troubleshooting <a name="Troubleshooting"></a>

### Deployment Issues:

#### General 
- Verify AWS credentials are configured correctly
- Ensure CDK is bootstrapped in your account/region
- Check the CloudFormation console for detailed error messages

#### `--app is required either in command-line, in cdk.json or in ~/.cdk.json`
Ensure you're in the right directory when running `cdk deploy`. see [Step 1](#deployment-directory)

### Runtime Issues:

- Check CloudWatch Logs for Lambda function errors
- Verify the IAM permissions are correct
- Ensure the Bedrock Agent and Action Group are configured correctly

**Common errors you might encounter:**

- "Resource not found": Ensure the required resources exist and the permissions are correct.
- "Access denied": Check the IAM roles and policies.
- "Invalid handler": Verify the Lambda function handler name.
- "Access denied when calling Bedrock": Verify Bedrock Model is available in the region and Model Access has been granted

## Development

### Key Stack Resources

The stack sets up the following key AWS resources: 

> [!Important]
>The resource names or name prefixes would change if the parameters in `cdk.json` are modified from their default values before creating the stack

- Claims Submission Bucket - Used to store incoming CMS 1500 claim forms
  - bucket name prefix `claims-review-bdaclaimsreviewbucket`

- EventBridge Rule - To capture the event when a new claims form is submitted and stored in the Claims Submission Bucket
  - Rule name prefix `claims-review-bdaonclaimsubmission`

- Invoke Data Automation Lambda Function - A Lambda function to trigger Bedrock Data Automation job that gathers insights from the claims form.
  - Function Name Prefix `claims-review-bdainvokedataautomation`

- EventBridge Rule - To capture the event when a the BDA insight job is completed. The rules has a target Lambda function that then triggers Bedrock Agent
  - Rule name prefix `claims-review-bdadataautomationcompleted`

- Invoke Claim Verification Lambda Function - A Lambda function to trigger Bedrock Agent to a prompt to start claim verification steps.
  - Function Name Prefix `claims-review-bdainvokeverification`

- Bedrock Agent to review claims
  - Agent Nae `claims-review-agent`

- Bedrock Knowledge Base to store Claims Evidence of Coverage (EoC) documents for the various Insurance plans
  - Knowledge Base Name `claims-eoc-kb`

- OpenSearch Serverless Collection/Index to serve as vector store for the EoC documents embeddings
  - Collection Name `claims-vector-store`
  - Index Name `claims_eoc_index`
  
- Custom resource with Lambda function to create Opensearch vector index 
  - function name prefix `claims-review-vectorstorecreatevectorindex`

- Aurora PostgreSQL Serverless Database
  - cluster name prefix `claims-review-auroraaurorapostgrescluster`
  - database name `claimdatabase`

- Custom resource with Lambda function to create initial claims database schema and sample data
  - function name prefix `claims-review-auroraSchemaExecutor`

- S3 Bucket to store Claims EoC documents
  - bucket name prefix `claims-review-claimseockbclaimseockbdatasource`

- EventBridge rule to match event when Claim EoC documents are added/updated. The rule triggers the lambda function to start ingestion job
  - rule name prefix `claims-review-claimseockbons3objectcreateupdaterule`

- Lambda Function to trigger datasource Sync for Claims EoC Knowledge Base
  - function name prefix `claims-review-datasourcesynclambdafunction`

### Project Structure
<details>
  <summary>Click for Project Structure</summary>

```
guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation/
├── assets/
│   ├── data/
│   │   ├── claims_review/
│   │   │   ├── cms_1500/
│   │   │   │   ├── sample1_cms-1500-P.pdf
│   │   │   │   ├── sample2_cms-1500-P.pdf
│   │   │   │   └── sample3_cms-1500-P.pdf
│   │   │   └── eoc/
│   │   │       ├── Evidence_of_Coverage_-_AnyHealth_Plus.pdf
│   │   │       ├── Evidence_of_Coverage_-_AnyHealth_Premium.pdf
│   │   │       └── Evidence_of_Coverage_-_AnyHealth_Standard.pdf
├── claims-cli.bat
├── claims-cli.sh
├── deployment/
│   ├── app.py
│   ├── cdk.json
│   ├── docs/
│   │   ├── b_claims_review_01_deploy.md
│   │   └── b_claims_review_02_run_flow.md
│   ├── lambda/
│   │   ├── claims_review/
│   │   │   ├── blueprint_creation/
│   │   │   │   └── index.py
│   │   │   ├── claims_review_agent_actions/
│   │   │   │   └── index.py
│   │   │   ├── create_vector_index/
│   │   │   │   └── index.py
│   │   │   ├── datasource_sync/
│   │   │   │   └── index.py
│   │   │   ├── invoke_data_automation/
│   │   │   │   ├── bda_wrapper.py
│   │   │   │   └── index.py
│   │   │   ├── invoke_verification/
│   │   │   │   ├── bedrock_agent_runtime_wrapper.py
│   │   │   │   └── index.py
│   │   │   ├── layer/
│   │   │   │   └── requirements.txt
│   │   │   └── manage_schema/
│   │   │       └── index.py
│   │   └── lending_flow/
│   │       ├── documents_post_processor/
│   │       │   └── index.py
│   │       ├── documents_processor/
│   │       │   └── index.py
│   │       ├── samples_post_processor/
│   │       │   └── index.py
│   │       └── samples_processor/
│   │           └── index.py
│   ├── requirements.txt
│   └── stacks/
│       ├── claims_review_stack/
│       │   ├── agent.py
│       │   ├── aurora_postgres.py
│       │   ├── document_automation.py
│       │   ├── knowledge_base.py
│       │   ├── prompts/
│       │   │   └── claims_review_agent.py
│       │   ├── schemas/
│       │   │   ├── claims_review_openapi.json
│       │   │   ├── create_database_schema.sql
│       │   │   └── delete_database_schema.sql
│       │   └── vector_store.py
├── README.md
├── source/
│   └── claims_review_app/
│       └── claims-cli.py
├── source.bat
```
</details>


### Customize the Stack
#### Customize Stack Parameters <a name="customize_stack_parameters"></a>
The stack uses context values in `cdk.json` file to store default parameters used for stack creation. To use your own values, you can either:
1. Modify the values for the specific keys in `cdk.json`, or;
2. use --context parameter with the `cdk deploy` command to override the values, for example 
`cdk deploy claims-review --context blueprint_name=yyyyy`

#### Customize the Claims Review Bedrock Agent prompt
The prompt instruction used to create the agent is in the `deployment/stacks/claims_review_stack/prompts/claims_review_agent.py`.
To Customize the agent instruction: 
1. Update the text set to variable `claims_review_agent_instruction`
2. save the changes
3. deploy the stack again using instructions in [6. Deploy the stack](#deploy-the-stack)

#### Manage Action Group schema 
- The action group API schema used for the agent action group is in  `deployment/stacks/claims_review_stack/schemas/claims_review_openapi.json`
- The Lambda functions backing the action group APIs are in `deployment/lambda/claims_review/claims_review_agent_actions/index.py`.
- The Database schema for the claim database (Aurora Postgres Serverless) is in `deployment/stacks/claims_review_stack/schemas/create_database_schema.sql`

To Customize the action group API schema:
1. Update the api schema in the file using OpenAPI 3.0 format
2. If necessary, make changes to the action group labmda function. 
3. Make necessary changes to the database schema
3. Save all the changes
4. Deploy the stack again using instructions in [6. Deploy the stack](#deploy-the-stack)

> [!Important]
>In case of breaking/incompatible changes to the database schema, it might be neccesary to delete and redeploy the stack. Follow the steps in [Cleanup](#cleanup) and [6. Deploy the stack](#deploy-the-stack)

#### Update stack resources
The `claims-review` stack has the following main source code files associated with it - 

- `deployment/stacks/claims_review_stack/agent.py` - The top-level `claims-review` stack that creates bedrock agent resources and uses custom construct to create and configure other related resources include the bedrock knowledge base, vector store, the aurora databaseand BDA automation.

- `deployment/stacks/claims_review_stack/vector_store.py` - Vector store resources include opensearch serverless collection and a Custom resource lambda function to create the vector index for the claims EoC knowledge base

- `deployment/stacks/claims_review_stack/knowledge_base.py` - A construct encapsulating resources required for the bedrock knowledge base including datasource buckets, datasources, the knowledge base itself and KB logging configuration


- `deployment/stacks/claims_review_stack/document_automation.py` - A construct encapsulating resources related to bedrock document automation, include the input/output s3 buckets, lambda function to invoke bda for insights

- `deployment/stacks/claims_review_stack/aurora_postgres.py` - Aurora Postgres database resources for the claims review database including, aurora cluster, database and initial schema creation

- `deployment/lambda/claims_review` - Function code for Lambda functions used in the claims-review stack. The main functions are - 
  - `deployment/lambda/claims_review/claims_review_agent_actions` - Bedrock Agent Action group API functions
  
  - `deployment/lambda/claims_review/create_vector_index` - Function to create the vector index as part of CDK deployment
  
  - `deployment/lambda/claims_review/datasource_sync` - Function to trigger Bedrock Knowledge Base datasource sync as new documents are uploaded to the backing datasource s3 bucket
  
  - `deployment/lambda/claims_review/invoke_data_automation` - function to trigger the BDA insight job after a new claim form is submitted

  - `deployment/lambda/claims_review/invoke_verification` - function to trigger claims review bedrock agent after the BDA insight job is completed and claim form data extracted output is available.

  - `deployment/lambda/claims_review/manage_schema` - function to create/update Aurora database schema as part of CDK deployment 

To update stack resources - 

1. Update the associated stack or construct file.
2. Update the Lambda function code in the respective directories, if necessary
3. Run `cdk diff claims-review` to review the changes.
4. Deploy the changes with `cdk deploy claims-review`.

## Cleanup  <a name="cleanup"></a>
 
1. Ensure that the S3 Buckets for claims submission, claims review and claims Eoc are empty. Save any documents that you would like to retain in an alternate location.

2. Change to the `deployment` directory for the guidance repository
   ```
   cd guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation
   ```
 
1. Destroy the stack
    ```bash
    cdk destroy claims-review
    ```

## Contributing

1. Create a new branch for features.
2. Update the documentation as needed.
3. Test the changes thoroughly.
4. Submit a pull request.

## Useful Links

- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/index.html)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Amazon Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html)


[screenshot_stack_create_complete]: ../../assets/screenshots/claims_review_docs/stack_create_complete.jpg