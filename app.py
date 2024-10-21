import streamlit as st
import pandas as pd
import re
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to filter URLs by regex pattern
def filter_by_regex(data, pattern):
    return data[data['Top pages'].apply(lambda x: bool(re.search(pattern, x)))]

# Function to calculate absolute and relative difference
def calculate_differences(metric_test, metric_control):
    abs_diff = metric_test - metric_control
    if metric_control != 0:
        rel_diff = (abs_diff / metric_control) * 100
    else:
        rel_diff = float('nan')
    return abs_diff, rel_diff

# Streamlit interface
st.title("GSC Page Group Analysis")

# Upload CSV file
uploaded_file = st.file_uploader("Upload GSC CSV", type="csv")
if uploaded_file is not None:
    # Read CSV into a DataFrame
    data = pd.read_csv(uploaded_file)
    
    # Convert CTR (string with %) to numeric for easier handling
    data['CTR'] = data['CTR'].str.rstrip('%').astype(float) / 100
    
    # User inputs for deployment date range and regex
    test_regex = st.text_input("Enter regex for Test group", "")
    control_regex = st.text_input("Enter regex for Control group (optional)", "")
    
    # Select test date range
    test_start = st.date_input("Test Start Date")
    test_end = st.date_input("Test End Date")
    
    # Automatically calculate the control period
    if test_start and test_end:
        test_period_length = (test_end - test_start).days
        control_end = test_start - timedelta(days=1)
        control_start = control_end - timedelta(days=test_period_length)
        st.write(f"Control period automatically set to: {control_start} to {control_end}")
    
    if st.button("Analyze"):
        # Filter test group using regex
        test_group = filter_by_regex(data, test_regex)
        
        # Filter control group, default to everything else if no regex provided
        if control_regex:
            control_group = filter_by_regex(data, control_regex)
        else:
            control_group = data[~data.index.isin(test_group.index)]
        
        # Sum metrics for test and control periods
        test_metrics = test_group[['Clicks', 'Impressions', 'CTR']].sum()
        control_metrics = control_group[['Clicks', 'Impressions', 'CTR']].sum()

        # Calculate differences for each metric
        differences = []
        for metric in ['Clicks', 'Impressions', 'CTR']:
            abs_diff, rel_diff = calculate_differences(test_metrics[metric], control_metrics[metric])
            differences.append({
                "Metric": metric,
                "Test Group Absolute Difference": abs_diff,
                "Test Group Relative Difference (%)": rel_diff
            })
        
        # Display grouped URLs
        st.subheader("Test Group URLs")
        st.write(test_group)
        
        st.subheader("Control Group URLs")
        st.write(control_group)

        # Display metric differences
        st.subheader("Differences in Metrics")
        st.write(pd.DataFrame(differences))

# Logging for debugging
if uploaded_file is None:
    logging.info("Waiting for file upload...")
else:
    logging.info("File uploaded and analysis in progress.")
