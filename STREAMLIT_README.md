# Claims Processing Dashboard - Streamlit UI

A user-friendly web interface for the Claims Processing system built with Streamlit.

## Features

- **Submit Claims**: Upload claim forms (PDF/images) with drag-and-drop interface
- **Upload EOC Documents**: Add Evidence of Coverage documents to the knowledge base
- **View Claims**: Browse all submitted claims with their reference IDs
- **View Claim Output**: Check processing results for specific claims
- **System Status**: Monitor deployment and configuration status
- **Ingestion Jobs**: Track document processing jobs

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r streamlit_requirements.txt
   ```

2. **Ensure AWS Configuration**:
   - AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
   - Proper permissions for CloudFormation, S3, and Bedrock services
   - Claims review stack deployed

3. **Run the Application**:
   ```bash
   # Option 1: Direct command
   streamlit run streamlit_app.py
   
   # Option 2: Using batch file (Windows)
   run_streamlit.bat
   ```

4. **Access the Dashboard**:
   - Open your browser to `http://localhost:8501`

## Usage Guide

### Submit Claim
1. Navigate to "Submit Claim" page
2. Upload your claim form (PDF or image)
3. Click "Submit Claim"
4. Note the generated Claim Reference ID

### Upload EOC Document
1. Go to "Upload EOC Document" page
2. Upload Evidence of Coverage PDF
3. Wait for processing to complete
4. Document will be added to the knowledge base

### View Claims
1. Visit "View Claims" page
2. See all submitted claims in a table format
3. Use "Refresh Claims List" to update
4. Click "View Ingestion Jobs" to see processing status

### View Claim Output
1. Go to "View Claim Output" page
2. Enter the Claim Reference ID
3. Click "Get Claim Output"
4. View formatted results or raw JSON

### System Status
1. Check "System Status" page
2. Verify deployment status
3. View system configuration
4. Read usage instructions

## Architecture Integration

This Streamlit UI integrates with the existing Claims Processing architecture:

- **Frontend**: Streamlit web interface
- **Backend**: Existing ClaimsCLI class
- **AWS Services**: 
  - S3 for document storage
  - Bedrock Data Automation for processing
  - Bedrock Knowledge Base for EOC documents
  - Bedrock Agent for claim review
  - CloudFormation for infrastructure

## Troubleshooting

**Common Issues:**

1. **Import Error**: Ensure `claims-cli.py` is in the correct location
2. **AWS Credentials**: Verify AWS configuration and permissions
3. **Stack Not Found**: Ensure the claims-review stack is deployed
4. **Port Conflict**: Change port in `run_streamlit.bat` if 8501 is in use

**Error Messages:**
- "Could not import ClaimsCLI": Check file paths and dependencies
- "Failed to initialize Claims CLI": Verify AWS credentials and region
- "Stack not found": Deploy the claims-review CloudFormation stack

## Development

To extend the UI:

1. **Add New Pages**: Create new functions and add to navigation
2. **Enhance Styling**: Use Streamlit components and CSS
3. **Add Features**: Integrate additional CLI functionality
4. **Error Handling**: Improve user feedback and error messages

## Security Notes

- Ensure proper AWS IAM permissions
- Use secure credential management
- Consider VPC deployment for production
- Implement proper logging and monitoring