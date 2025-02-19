# Instructions For Using Blueprints To Process Medical Insurance Claims

In the second flow, we will submit documents that will be processed and the extracted contents stored in an Amazon Bedrock Knowledge Base, to create a Retrieval Augmented Generation (RAG) database.  We will then build a Bedrock Agent to process an insurance claim. The agent will use Generative AI to determine the eligibility of the claim, and update the claims database.

You have now completed the install and setup of the solution to process Insurance Claims. Our deployed solution has the components shown. If you have not completed this step, please go back and complete the deployment steps [here](https://github.com/aws-solutions-library-samples/guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation/blob/main/deployment/docs/b_claims_review_01_deploy.md) before proceeding. 

<img src="../../assets/architectures/b_claims_review_architecture.png" width="800" />


BDA is a generative-AI powered capability of Amazon Bedrock that enables you to automate your end-to-end Intelligent Document Processing (IDP) workflows quickly, accurately and at scale. A blueprint is a structural representation of your desired output for a specific document type (e.g. invoices, drivers licenses or IRS form 1099-INT). We then feed new unseen documents into the solution, for BDA to detect the document type, apply the correct blueprint and send the extracted results for downstream processing.

## Adding Content to the Insurance EOC Knowledge Base
We now need to populate the knowledge base with the content from our claims Evidence of Coverage documents. There are sample documents available in the path `assets/data/claims_review/eoc`.  We can use the claims-cli command-line interface add these document to the claims EOC knowledge base.

More details - [Sync your data with your Amazon Bedrock knowledge base][Sync_your_data_with_your_Amazon_Bedrock_knowledge_base]


> [!Note]
>Before continuing: 
1. Ensure you are in the root directory of this repository which is `guidance-for-multimodal-data-processing-using-amazon-bedrock-data-automation`
2. Ensure you have the python virtual environment still active. See [Create and activate a virtual environment](./b_claims_review_01_deploy.md#create_env)

Run the following commands to add each of the EoC documents to S3 and start the ingestion process
```
 ./claims-cli.sh upload-eoc-document --file assets/data/claims_review/eoc/Evidence_of_Coverage_-_AnyHealth_Standard.pdf 
 ./claims-cli.sh upload-eoc-document --file assets/data/claims_review/eoc/Evidence_of_Coverage_-_AnyHealth_Plus.pdf 
 ./claims-cli.sh upload-eoc-document --file assets/data/claims_review/eoc/Evidence_of_Coverage_-_AnyHealth_Premium.pdf 
```

The output shows the Ingestion process starting and completing.
![Claims EoC Ingestion][screenshot_claims_eoc_ingestion]

## Accessing the Insurance EOC Knowledge Base

In this step, we will use Bedrock in the AWS Console to view and access the Insurance EOC Knowledge Base. We will use the console to issue prompts 

1. Open the Amazon Bedrock Console and Click on `Knowledge Bases` under `Builder Tools` in the the sidebar to navigate to the Knowledge Bases view
![Navigate to Knowledge Base Page][screenshot_view_kb]

2. In the Knowledge Bases view, select the Knowledge Base named `claims-eoc-kb` and click on `Test Knowledge Base`
![Test Knowledge Base][screenshot_test_kb]

3. In the `Test Knowledge Base` pane on the right side of the page, Click Select model, select a model of choice from the available models and Click Apply.

> [!Note]
> Choose the model of your choice and please follow the model provider acceptable end user policy. Results will vary based on the foundational model chosen
![Select Mode to Test Knowledge Base][screenshot_select_model]


4. With the model selected, we are ready to test our Claims Evidence of Coverage knowledge base. You can ask a question in natural language to retrieve relevant response. For example

 ```
  What are the treatments covered under the Premium Plan?
 ```
![Ask KB][screenshot_ask_kb]

5. The Knowledge base retrieves the relevant EoC document for the Premium plan and responds to the question

    ![KB_Response][screenshot_kb_response]


## Processing of a Medical Insurance Claims

We will now submit a new lending application to BDA. BDA will process the insurance claim, and check for coverage against the EOC documents in the Knowledge Base. 

We can use the claims-cli again to do this. A few sample claims forms are available in `assets/data/claims_review/cms_155`

1. Upload a claim form using the cli. Keep a note of the `claim-reference-id` in the output 
 ```
 ./claims-cli.sh submit-claim --file assets/data/claims_review/cms_1500/sample1_cms-1500-P.pdf 

 ```
When the form is succesfully uploaded, the cli outputs a success mesage with a unique `claim reference id`

![Claim Submitted][screenshot_claim_submitted]

2. Wait for a few minutes and check the claim output using the cli.<a name=step2_claimreview></a>
 Keep a note of the `claim-reference-id` in the output 
  
  ```bash
  ./claims-cli.sh view-claim-output --claim-reference-id <<claim_reference_id_from_step1_output>>
  ```
An example output (screenshot below) of the command lists the summary of the automate review performed by the Bedrock Agent


> [!Note]
> Results will vary based on the foundational model chosen

![Claims Output][screenshot_claims_review_output]


 3. We can also look at available claim reference ids using the cli

  ```bash
 ./claims-cli.sh list-claims
  ```
We can get ClaimID and view claims in streamlit app
  ```bash
 pip install streamlit
 streamlit run app_claims.py

  ```

## Viewing Logs and Troubleshooting

#### Error: Claim output not found for claim reference ID: <<claim_reference_id>>. Please try again later when trying to view claim output in [Step 2](#step2_claimreview)
This means an error in the claims review process. We can look at CloudWatch Logs to identify the root cause of the error

1. View and analyse log stream for the BDA invoke automation lambda function for any errors
2. View and analyse log stream logs for the BDA invoke claim verification lambda function for any errors
3. View and analyse log stream logs for the Bedrock Agent Actions lambda function for any errors




[Sync_your_data_with_your_Amazon_Bedrock_knowledge_base]: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-data-source-sync-ingest.html

[screenshot_select_model]: ../../assets/screenshots/claims_review_docs/select-model-v2.jpg
[screenshot_ask_kb]: ../../assets/screenshots/claims_review_docs/ask-kb.jpg
[screenshot_test_kb]: ../../assets/screenshots/claims_review_docs/test-kb.jpg
[screenshot_kb_response]: ../../assets/screenshots/claims_review_docs/KB-result.jpg
[screenshot_view_kb]: ../../assets/screenshots/claims_review_docs/open-kb-view.jpg
[screenshot_claim_submitted]: ../../assets/screenshots/claims_review_docs/claimsubmission-output.jpg
[screenshot_claim_eoc_ingestion]: ../../assets/screenshots/claims_review_docs/claim-eoc-ingestion.jpg
[screenshot_claims_review_output]: ../../assets/screenshots/claims_review_docs/claims_review_output.jpg
[screenshot_claims_eoc_ingestion]: ../../assets/screenshots/claims_review_docs/claim-eoc-ingestion.jpg
