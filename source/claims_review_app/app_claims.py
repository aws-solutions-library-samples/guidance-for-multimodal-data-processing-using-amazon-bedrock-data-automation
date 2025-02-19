import streamlit as st
import subprocess
import re



def list_claims():
    try:
        result = subprocess.run(['python3', 'claims-cli.py', 'list-claims'], capture_output=True, text=True)
        if result.returncode == 0:
            # Use regex to find claim IDs in the output
            claim_ids = re.findall(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', result.stdout)
            return claim_ids
        else:
            return [f"Error: {result.stderr}"]
    except Exception as e:
        return [f"Exception: {str(e)}"]

def view_claim_output(claim_id):
    try:
        result = subprocess.run(['python3', 'claims-cli.py', 'view-claim-output', '--claim-reference-id', claim_id], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {str(e)}"

st.title("Claims App")

if st.button("List Claims"):
    claims = list_claims()
    if claims:
        claims_list = "\n".join([f"- {claim}" for claim in claims])
        st.sidebar.markdown(f"### Claims List\n{claims_list}")

claim_id = st.text_input("Enter Claim ID")

if st.button("View Claim Output"):
    if claim_id:
        output = view_claim_output(claim_id)
        st.markdown(output)
    else:
        st.warning("Please enter a Claim ID.")