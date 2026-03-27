import streamlit as st
import sys
import os
import json
from datetime import datetime
import pandas as pd
import re
import boto3

# Import ClaimsCLI from claims-cli.py
current_dir = os.path.dirname(os.path.abspath(__file__))
source_path = os.path.join(current_dir, 'source', 'claims_review_app')
sys.path.insert(0, source_path)

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("claims_cli", os.path.join(source_path, "claims-cli.py"))
    claims_cli_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(claims_cli_module)
    ClaimsCLI = claims_cli_module.ClaimsCLI
except Exception as e:
    st.error(f"Could not import ClaimsCLI: {str(e)}")
    st.error(f"Looking for claims-cli.py in: {source_path}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Claims Processing Dashboard",
    page_icon="📋",
    layout="wide"
)

# Initialize session state
if 'cli' not in st.session_state:
    try:
        st.session_state.cli = ClaimsCLI()
    except Exception as e:
        st.error(f"Failed to initialize Claims CLI: {str(e)}")
        st.stop()

def generate_ai_summary(content):
    """Generate AI summary using Nova Pro model"""
    try:
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        prompt = f"""Please provide a concise summary of this claim review report:

{content}

Summarize the key points including:
- Claim status
- Patient name
- Patient information verification results 
- Services coverage details
- Any important findings or recommendations

Keep the summary clear and professional."""
        
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1000,
                    "temperature": 0.1
                }
            })
        )
        
        result = json.loads(response['body'].read())
        summary = result['output']['message']['content'][0]['text']
        
        return summary
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def parse_claim_output(raw_content):
    """Parse claim output and display tables properly"""
    content = raw_content.strip().strip('"')
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if '|' in line and line.count('|') >= 3:
            # Collect table lines
            table_lines = []
            while i < len(lines) and '|' in lines[i].strip():
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 3:
                headers = [col.strip() for col in table_lines[0].split('|')[1:-1]]
                rows = []
                for row_line in table_lines[2:]:
                    row = [col.strip() for col in row_line.split('|')[1:-1]]
                    if len(row) == len(headers):
                        rows.append(row)
                
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                    st.dataframe(df, use_container_width=True)
                    st.write("")
        else:
            if line:
                st.write(line)
            i += 1

def delete_single_claim(claim_id):
    """Delete a single claim from both buckets"""
    try:
        s3_client = st.session_state.cli.s3_client
        submission_bucket = st.session_state.cli.get_claims_submission_bucket_name()
        review_bucket = st.session_state.cli.get_claims_review_bucket_name()
        
        deleted_count = 0
        
        # Delete from submission bucket
        response = s3_client.list_objects_v2(Bucket=submission_bucket, Prefix=f"{claim_id}/")
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=submission_bucket,
                Delete={'Objects': objects_to_delete}
            )
            deleted_count += len(objects_to_delete)
        
        # Delete from review bucket
        response = s3_client.list_objects_v2(Bucket=review_bucket, Prefix=f"{claim_id}/")
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=review_bucket,
                Delete={'Objects': objects_to_delete}
            )
            deleted_count += len(objects_to_delete)
        
        st.success(f"✅ Successfully deleted claim {claim_id} ({deleted_count} files)")
        
    except Exception as e:
        st.error(f"Error deleting claim {claim_id}: {str(e)}")

def main():
    st.title("📋 Claims Processing Dashboard")
    st.markdown("---")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Submit Claim", "Upload EOC Document", "View Claims", "View Claim Output", "System Status"]
    )
    
    if page == "Submit Claim":
        submit_claim_page()
    elif page == "Upload EOC Document":
        upload_eoc_page()
    elif page == "View Claims":
        view_claims_page()
    elif page == "View Claim Output":
        view_claim_output_page()
    elif page == "System Status":
        system_status_page()

def submit_claim_page():
    st.header("📤 Submit New Claim")
    
    uploaded_file = st.file_uploader(
        "Choose a claim form file",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        help="Upload your claim form (PDF or image file)"
    )
    
    if uploaded_file is not None:
        st.info(f"File: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        if st.button("Submit Claim", type="primary"):
            with st.spinner("Submitting claim..."):
                try:
                    temp_path = f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    bucket_name = st.session_state.cli.get_claims_submission_bucket_name()
                    claim_id = st.session_state.cli.submit_claim(temp_path, bucket_name)
                    
                    os.remove(temp_path)
                    
                    if claim_id:
                        st.success("✅ Claim submitted successfully!")
                        st.info(f"**Claim Reference ID:** `{claim_id}`")
                    else:
                        st.error("❌ Failed to submit claim")
                    
                except Exception as e:
                    st.error(f"Error submitting claim: {str(e)}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

def upload_eoc_page():
    st.header("📄 Upload Evidence of Coverage Document")
    
    uploaded_file = st.file_uploader(
        "Choose an EOC document",
        type=['pdf'],
        help="Upload Evidence of Coverage document (PDF only)"
    )
    
    if uploaded_file is not None:
        st.info(f"File: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        if st.button("Upload EOC Document", type="primary"):
            with st.spinner("Uploading and processing document..."):
                try:
                    temp_path = f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    bucket_name = st.session_state.cli.get_eoc_bucket_name()
                    st.session_state.cli.add_eoc_document(temp_path, bucket_name)
                    
                    os.remove(temp_path)
                    
                    st.success("✅ EOC document uploaded and processed successfully!")
                    
                except Exception as e:
                    st.error(f"Error uploading EOC document: {str(e)}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

def view_claims_page():
    st.header("📋 View All Claims")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Refresh Claims List", type="secondary"):
            st.rerun()
    
    with col2:
        if st.button("View Ingestion Jobs", type="secondary"):
            st.session_state.show_ingestion_jobs = True
    
    with col3:
        if st.button("🗑️ Delete All Claims", type="secondary"):
            st.session_state.show_delete_confirmation = True
    
    try:
        bucket_name = st.session_state.cli.get_claims_submission_bucket_name()
        s3_client = st.session_state.cli.s3_client
        
        result = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
        
        if 'CommonPrefixes' in result:
            claim_ids = [prefix['Prefix'].rstrip('/') for prefix in result['CommonPrefixes']]
            
            st.subheader(f"Found {len(claim_ids)} claims:")
            
            # Display claims with individual action buttons
            for i, claim_id in enumerate(claim_ids):
                col1, col2, col3 = st.columns([6, 1, 1])
                
                with col1:
                    st.write(f"{i+1}. {claim_id}")
                
                with col2:
                    if st.button("View", key=f"view_{claim_id}"):
                        st.session_state.selected_claim = claim_id
                
                with col3:
                    if st.button("Delete", key=f"delete_{claim_id}", type="secondary"):
                        delete_single_claim(claim_id)
                        st.rerun()
            
        else:
            st.info("No claims found in the system.")
            
    except Exception as e:
        st.error(f"Error retrieving claims: {str(e)}")
    
    if st.session_state.get('show_ingestion_jobs', False):
        st.subheader("📊 Ingestion Jobs Status")
        try:
            kb_id = st.session_state.cli.get_eoc_kb_id()
            datasource_id = st.session_state.cli.get_eoc_kb_datasource_id()
            response = st.session_state.cli.bedrock_agent_client.list_ingestion_jobs(
                knowledgeBaseId=kb_id,
                dataSourceId=datasource_id
            )
            jobs = sorted(response["ingestionJobSummaries"], key=lambda x: x['startedAt'], reverse=True)
            
            if jobs:
                job_data = []
                for job in jobs:
                    job_data.append({
                        'Job ID': job['ingestionJobId'],
                        'Status': job['status'],
                        'Documents Indexed': job['statistics']['numberOfNewDocumentsIndexed'],
                        'Started At': job['startedAt'].strftime('%Y-%m-%d %H:%M:%S'),
                        'Updated At': job['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                df_jobs = pd.DataFrame(job_data)
                st.dataframe(df_jobs, use_container_width=True)
            else:
                st.info("No ingestion jobs found.")
                
        except Exception as e:
            st.error(f"Error retrieving ingestion jobs: {str(e)}")
        
        st.session_state.show_ingestion_jobs = False
    
    if st.session_state.get('show_delete_confirmation', False):
        st.warning("⚠️ **WARNING: This will permanently delete ALL claims from both buckets!**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirm Delete All", type="primary"):
                delete_all_claims()
                st.session_state.show_delete_confirmation = False
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel", type="secondary"):
                st.session_state.show_delete_confirmation = False
                st.rerun()

def delete_all_claims():
    try:
        s3_client = st.session_state.cli.s3_client
        submission_bucket = st.session_state.cli.get_claims_submission_bucket_name()
        review_bucket = st.session_state.cli.get_claims_review_bucket_name()
        
        deleted_count = 0
        
        response = s3_client.list_objects_v2(Bucket=submission_bucket)
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=submission_bucket,
                Delete={'Objects': objects_to_delete}
            )
            deleted_count += len(objects_to_delete)
        
        response = s3_client.list_objects_v2(Bucket=review_bucket)
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=review_bucket,
                Delete={'Objects': objects_to_delete}
            )
            deleted_count += len(objects_to_delete)
        
        st.success(f"✅ Successfully deleted {deleted_count} files from all claims!")
        
    except Exception as e:
        st.error(f"Error deleting claims: {str(e)}")

def view_claim_output_page():
    st.header("🔍 View Claim Output")
    
    # Check if a claim was selected from the View Claims page
    if 'selected_claim' in st.session_state:
        claim_reference_id = st.session_state.selected_claim
        st.info(f"Selected claim: {claim_reference_id}")
        del st.session_state.selected_claim
    else:
        try:
            bucket_name = st.session_state.cli.get_claims_submission_bucket_name()
            s3_client = st.session_state.cli.s3_client
            result = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
            
            if 'CommonPrefixes' in result:
                claim_ids = [prefix['Prefix'].rstrip('/') for prefix in result['CommonPrefixes']]
                claim_ids.insert(0, "Select a claim...")
                
                claim_reference_id = st.selectbox(
                    "Select Claim Reference ID:",
                    options=claim_ids,
                    index=0
                )
            else:
                st.info("No claims found in the system.")
                return
                
        except Exception as e:
            st.error(f"Error retrieving claims: {str(e)}")
            return
    
    if st.button("Get Claim Output", type="primary") and claim_reference_id != "Select a claim...":
        with st.spinner("Retrieving claim output..."):
            try:
                claim_output_s3_object = st.session_state.cli.s3_client.get_object(
                    Bucket=st.session_state.cli.get_claims_review_bucket_name(),
                    Key=f"{claim_reference_id}/claim_output.json"
                )
                
                raw_content = claim_output_s3_object['Body'].read().decode('utf-8')
                
                st.success("✅ Claim output retrieved successfully!")
                
                if raw_content.strip().startswith(('{', '[')):
                    try:
                        claim_output = json.loads(raw_content)
                        st.subheader("Claim Output Details:")
                        st.json(claim_output)
                        
                        with st.expander("Raw JSON Output"):
                            st.code(json.dumps(claim_output, indent=2), language='json')
                    except json.JSONDecodeError:
                        st.subheader("Claim Output Details:")
                        st.markdown(raw_content)
                        
                        with st.expander("Raw Content"):
                            st.code(raw_content, language='text')
                else:
                    # Extract key information for summary
                    content = raw_content.strip().strip('"')
                    
                    # Summary section
                    st.subheader("📊 Claim Summary")
                    
                    # Extract claim status
                    if "ADJUDICATOR_REVIEW" in content:
                        st.error("🔴 Status: ADJUDICATOR_REVIEW")
                    elif "IN_PROGRESS" in content:
                        st.info("🟡 Status: IN_PROGRESS")
                    else:
                        st.success("🟢 Status: PROCESSED")
                    
                    
                    # Find patient name
                    patient_name_match = re.search(r'Patient Name\s*\|\s*([^|]+)\s*\|', content)
                    if patient_name_match:
                        patient_name = patient_name_match.group(1).strip()
                        st.info(f"**Patient:** {patient_name}")
                    
                    # Find patient details table
                    patient_matches = re.findall(r'\|\s*([^|]+)\s*\|\s*[^|]*\s*\|\s*[^|]*\s*\|\s*(Match|No Match)\s*\|', content)
                    
                    if patient_matches:
                        matched_fields = [field.strip() for field, status in patient_matches if status == "Match"]
                        unmatched_fields = [field.strip() for field, status in patient_matches if status == "No Match"]
                        
                        if matched_fields:
                            st.success(f"✅ **Matched Fields:** {', '.join(matched_fields)}")
                        if unmatched_fields:
                            st.error(f"❌ **Unmatched Fields:** {', '.join(unmatched_fields)}")
                    
                    
                    # Find services table
                    service_matches = re.findall(r'\|\s*([^|]+)\s*\|[^|]*\|[^|]*\|[^|]*\|\s*(Covered|Not Covered)\s*\|', content)
                    
                    if service_matches:
                        covered_services = [service.strip() for service, status in service_matches if status == "Covered"]
                        not_covered_services = [service.strip() for service, status in service_matches if status == "Not Covered"]
                        
                        if covered_services:
                            st.success("✅ **Covered Services:**")
                            for service in covered_services:
                                st.write(f"  • {service}")
                        
                        if not_covered_services:
                            st.error("❌ **Not Covered Services:**")
                            for service in not_covered_services:
                                st.write(f"  • {service}")
                    
                    st.markdown("---")
                    
                    # AI Summary using Nova Pro
                    st.subheader("📋 Detailed Analysis")
                    with st.spinner("Generating summary with Nova Pro..."):
                        summary = generate_ai_summary(content)
                        if "Error" not in summary:
                            st.write(summary)
                        else:
                            st.error(summary)
                    
                    st.markdown("---")
    
                    with st.expander("📄 Raw Content"):
                        st.code(raw_content, language='text')
                    
            except st.session_state.cli.s3_client.exceptions.NoSuchKey:
                st.error(f"❌ Claim output not found for ID: {claim_reference_id}")
                st.info("The claim may still be processing. Please try again later.")
            except Exception as e:
                st.error(f"Error retrieving claim output: {str(e)}")

def system_status_page():
    st.header("🔧 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Deployment Status")
        if st.button("Check Deployment Status"):
            try:
                response = st.session_state.cli.cf_client.describe_stacks(
                    StackName=st.session_state.cli.stack_name
                )
                status = response['Stacks'][0]['StackStatus']
                
                if status == 'CREATE_COMPLETE' or status == 'UPDATE_COMPLETE':
                    st.success(f"✅ Stack Status: {status}")
                else:
                    st.warning(f"⚠️ Stack Status: {status}")
                    
            except Exception as e:
                st.error(f"Error checking deployment status: {str(e)}")
    
    with col2:
        st.subheader("System Configuration")
        try:
            config_info = {
                "Claims Submission Bucket": st.session_state.cli.get_claims_submission_bucket_name(),
                "Claims Review Bucket": st.session_state.cli.get_claims_review_bucket_name(),
                "EOC Knowledge Base ID": st.session_state.cli.get_eoc_kb_id(),
                "Claims Review Agent ID": st.session_state.cli.get_claims_review_agent_id(),
            }
            
            for key, value in config_info.items():
                st.info(f"**{key}:** {value}")
                
        except Exception as e:
            st.error(f"Error retrieving system configuration: {str(e)}")
    
    st.subheader("📖 How to Use This System")
    st.markdown("""
    1. **Submit Claim**: Upload claim forms (PDF or images) to start the processing workflow
    2. **Upload EOC Document**: Add Evidence of Coverage documents to the knowledge base
    3. **View Claims**: See all submitted claims and their reference IDs
    4. **View Claim Output**: Check the processing results for specific claims
    5. **System Status**: Monitor deployment and configuration status
    
    **Note**: After submitting a claim, it may take a few minutes to process. Check the claim output periodically.
    """)

if __name__ == "__main__":
    main()