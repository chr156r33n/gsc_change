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
def calculate_differences(metric_current, metric_previous):
    abs_diff = metric_current - metric_previous
    if metric_previous != 0:
        rel_diff = (abs_diff / metric_previous) * 100
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
        
        # Pre-test period
        pre_test_end = test_start - timedelta(days=1)
        pre_test_start = pre_test_end - timedelta(days=test_period_length)
        
        # Previous year same period
        prev_year_test_start = test_start - timedelta(days=365)
        prev_year_test_end = test_end - timedelta(days=365)
        
        st.write(f"Pre-test period: {pre_test_start} to {pre_test_end}")
        st.write(f"Previous year (same as test period): {prev_year_test_start} to {prev_year_test_end}")
    
    if st.button("Analyze"):
        # Filter test group using regex
        test_group = filter_by_regex(data, test_regex)
        
        # Filter control group, default to everything else if no regex provided
        if control_regex:
            control_group = filter_by_regex(data, control_regex)
        else:
            control_group = data[~data.index.isin(test_group.index)]
        
        # Sum metrics for test, pre-test, and previous year periods
        test_metrics_current = test_group[['Clicks', 'Impressions', 'CTR']].sum()
        test_metrics_previous = test_group[['Clicks', 'Impressions', 'CTR']].sum()  # For now, simulate data
        
        control_metrics_current = control_group[['Clicks', 'Impressions', 'CTR']].sum()
        control_metrics_previous = control_group[['Clicks', 'Impressions', 'CTR']].sum()  # For now, simulate data

        # Calculate differences for test and control groups
        test_differences = []
        control_differences = []
        for metric in ['Clicks', 'Impressions', 'CTR']:
            abs_diff_test, rel_diff_test = calculate_differences(test_metrics_current[metric], test_metrics_previous[metric])
            abs_diff_control, rel_diff_control = calculate_differences(control_metrics_current[metric], control_metrics_previous[metric])

            test_differences.append({
                "Metric": metric,
                "Test Group Absolute Difference": abs_diff_test,
                "Test Group Relative Difference (%)": rel_diff_test
            })

            control_differences.append({
                "Metric": metric,
                "Control Group Absolute Difference": abs_diff_control,
                "Control Group Relative Difference (%)": rel_diff_control
            })
        
        # Display grouped URLs
        st.subheader("Test Group URLs")
        st.write(test_group)
        
        st.subheader("Control Group URLs")
        st.write(control_group)

        # Display metric differences for test group
        st.subheader("Test Group Differences in Metrics (Pre-Test vs. Same Period Last Year)")
        st.write(pd.DataFrame(test_differences))

        # Display metric differences for control group
        st.subheader("Control Group Differences in Metrics (Pre-Test vs. Same Period Last Year)")
        st.write(pd.DataFrame(control_differences))

# Logging for debugging
if uploaded_file is None:
    logging.info("Waiting for file upload...")
else:
    logging.info("File uploaded and analysis in progress.")
