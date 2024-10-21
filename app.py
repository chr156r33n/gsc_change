import streamlit as st
import pandas as pd
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to filter URLs by regex pattern
def filter_by_regex(data, pattern):
    return data[data['Top pages'].apply(lambda x: bool(re.search(pattern, x)))]

# Function to calculate absolute and relative difference
def calculate_differences(df, metric, period1, period2):
    abs_diff = df[period1] - df[period2]
    rel_diff = (abs_diff / df[period2]) * 100
    return abs_diff, rel_diff

# Streamlit interface
st.title("GSC Page Group Analysis")

# Upload CSV file
uploaded_file = st.file_uploader("Upload GSC CSV", type="csv")
if uploaded_file is not None:
    # Read CSV into a DataFrame
    data = pd.read_csv(uploaded_file)
    
    # User inputs for deployment date range and regex
    test_regex = st.text_input("Enter regex for Test group", "")
    control_regex = st.text_input("Enter regex for Control group (optional)", "")
    
    # Select date ranges
    test_start = st.date_input("Test Start Date")
    test_end = st.date_input("Test End Date")
    pre_test_start = st.date_input("Pre-Test Start Date")
    pre_test_end = st.date_input("Pre-Test End Date")
    
    if st.button("Analyze"):
        # Filter test group using regex
        test_group = filter_by_regex(data, test_regex)
        
        # Filter control group, default to everything else if no regex provided
        if control_regex:
            control_group = filter_by_regex(data, control_regex)
        else:
            control_group = data[~data.index.isin(test_group.index)]
        
        # Calculate metrics for test and control groups
        for metric in ['Clicks', 'Impressions', 'CTR']:
            abs_diff_test, rel_diff_test = calculate_differences(test_group, metric, 'Clicks', 'Impressions')
            abs_diff_control, rel_diff_control = calculate_differences(control_group, metric, 'Clicks', 'Impressions')

        # Show grouped URLs
        st.subheader("Test Group URLs")
        st.write(test_group)
        
        st.subheader("Control Group URLs")
        st.write(control_group)

        st.subheader("Differences in Metrics")
        st.write("Absolute and Relative Differences (Test vs Pre-test and Year-over-Year)")

# Logging for debugging
if uploaded_file is None:
    logging.info("Waiting for file upload...")
else:
    logging.info("File uploaded and analysis in progress.")

