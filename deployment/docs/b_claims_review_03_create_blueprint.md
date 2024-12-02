# Instructions to create a Custom Blueprint for CMS 1500 Medical Claim Form in AWS Bedrock Document Automation

In this guide, we will create a custom blueprint for processing CMS 1500 medical claim forms using AWS Bedrock Document Automation (BDA). The CMS 1500 form is widely used for submitting medical claims to insurance providers in the United States.

## Step 1: Prepare Sample Document

To create a blueprint, you need to obtain a sample CMS 1500 filled form. You can find some samples in `assets/data/claims_review/cms` folder of the repository.

## Step 2: Navigate to Bedrock Data Autoation and Trigger Blueprint Generation

1. Navigate to the AWS Console
2. Search for "Bedrock" in the "Services" search bar and click 'Amazon Bedrock' in the search results
3. In the Bedrock console, click on the "Custom output setup" menu under Data Automation
   ![navigate_custom_output_setup][screenshot_nav_to_custom_output_setup]

3. In the Custom output setup screen, click on "Create Blueprint"
   ![navigate_create_blueprint][screenshot_nav_to_create_blueprint]

4. In the Create blueprint screen, select upload from computer, then click choose file.
   ![create_blueprint_view][screenshot_create_blueprint_view]

5. Browse to the sample CMS 1500 form in the repo at `assets/data/claims_review/cms_1500/sample1_cms-1500-P.pdf`, select the file and choose open 

6. Verify the document preview and click upload to store the file in S3. BDA creates an S3 bucket in your account to save the file.
   ![upload_blueprint_sample][screenshot_upload_blueprint_view]

7. Once the sample is uploaded, the Generate Blueprint button is enable. You can, optionally provide a prompt to create a blueprint.  If If you do not provide a prompt the Blueprint prompt AI will instead generate one.
   ![screenshot_blueprint_prompt][screenshot_blueprint_prompt]

8. Click on `Generate Blueprint` to start the BDA blueprint creation process
   ![screenshot_generate_blueprint][screenshot_generate_blueprint]

9. BDA would use the sample document and the prompt to generate a blueprint for extracting insights from the CMS 1500. Once the blueprint is created, BDA would prompt for a Blueprint name. Enter `claims-review-cms1500` 
   ![name_blueprint][screenshot_name_blueprint]

> [!Important]
>By default the claims review stack uses the blueprint name `claims-review-cms1500`. If you choose to use another name, then you could modify the cdk context variable in `cdk.json` and redeploy the stack. See [Customize Stack Parameters](b_claims_review_01_deploy.md#customize-stack-parameters-a-namecustomize_stack_parameters)


## Step 3: Create a Custom Blueprint

1. In your "cms-1500-claims-project", click the "Create Blueprint" button
2. Upload your sample CMS 1500 form
3. For the initial prompt, enter: "This is a CMS 1500 medical claim form. Please extract all the keys and values from the form, including patient information, provider details, diagnosis codes, and service lines."
4. Click the "Generate Blueprint" button

BDA will analyze the sample form and create a new reusable Blueprint for future CMS 1500 forms.

## Step 4: Review and Refine the Blueprint

1. Name the blueprint "cms-1500-medical-claim"
2. Review the extracted fields. You should see various sections including:
   - Patient and Insured Information
   - Physician or Supplier Information
   - Diagnosis Codes
   - Service Lines (potentially multiple)
3. If needed, manually add or adjust fields to ensure all critical information is captured

## Step 5: Add Blueprint to Project

1. Click "Add to Project" and select "Add to existing project"
2. Choose the "cms-1500-claims-project" we created earlier
3. Click "Save and exit blueprint prompt"

## Step 6: Test the Blueprint

1. Navigate back to your "cms-1500-claims-project"
2. On the "Custom Output" tab, select the "cms-1500-medical-claim" blueprint
3. Upload a different CMS 1500 form (not the one used to create the blueprint)
4. Click "Generate Results"

BDA will analyze the new form using your custom blueprint and extract the relevant information.

## Step 7: Refine and Iterate

1. Review the results of your test
2. If necessary, return to the blueprint and make adjustments:
   - Add missing fields
   - Refine field names for clarity
   - Adjust the initial prompt if certain areas need more attention
3. Repeat the testing process with various CMS 1500 forms to ensure consistency and accuracy

By following these steps, you'll have created a custom blueprint in AWS Bedrock Document Automation specifically designed to extract key information from CMS 1500 medical claim forms. This blueprint can be used to process large volumes of claims efficiently, supporting tasks such as claims processing, auditing, and data analysis in healthcare administration.

[screenshot_nav_to_custom_output_setup]: ../../assets/screenshots/claims_review_docs/navigate-to-bda.jpg
[screenshot_nav_to_create_blueprint]: ../../assets/screenshots/claims_review_docs/create-blueprint.jpg
[screenshot_create_blueprint_view]: ../../assets/screenshots/claims_review_docs/create-blueprint-view.jpg
[screenshot_upload_blueprint_view]: ../../assets/screenshots/claims_review_docs/upload-blueprint-sample.jpg
[screenshot_blueprint_prompt]: ../../assets/screenshots/claims_review_docs/blueprint-prompt.jpg
[screenshot_generate_blueprint]: ../../assets/screenshots/claims_review_docs/generate-blueprint.jpg
[screenshot_name_blueprint]: ../../assets/screenshots/claims_review_docs/name-blueprint.jpg