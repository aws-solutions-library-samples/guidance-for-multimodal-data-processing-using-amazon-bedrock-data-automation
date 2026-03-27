import pandas as pd
import streamlit as st

def display_claim_output(raw_content):
    """Parse and display claim output with tables formatted properly"""
    st.subheader("📋 Claim Analysis Results")
    
    # Clean content
    content = raw_content.strip().strip('"')
    lines = content.split('\n')
    
    current_section = []
    
    for line in lines:
        line = line.strip()
        
        # Check if this is a table line
        if '|' in line and line.count('|') >= 3:
            # Start collecting table
            table_lines = [line]
            continue_table = True
            
            # Look ahead to collect full table
            line_idx = lines.index(line) + 1
            while line_idx < len(lines) and continue_table:
                next_line = lines[line_idx].strip()
                if '|' in next_line:
                    table_lines.append(next_line)
                    line_idx += 1
                else:
                    continue_table = False
            
            # Process the table
            if len(table_lines) >= 3:
                headers = [col.strip() for col in table_lines[0].split('|')[1:-1]]
                rows = []
                
                for table_line in table_lines[2:]:  # Skip separator
                    if '|' in table_line:
                        row = [col.strip() for col in table_line.split('|')[1:-1]]
                        if len(row) == len(headers):
                            rows.append(row)
                
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                    st.dataframe(df, use_container_width=True)
                    st.write("")
        
        elif line and not any('|' in prev_line for prev_line in lines[max(0, lines.index(line)-2):lines.index(line)]):
            # Regular text (not part of table)
            st.write(line)