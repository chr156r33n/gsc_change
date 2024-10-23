import streamlit as st
import pandas as pd
import re
import logging
from datetime import timedelta
from io import StringIO

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create a sample CSV
def create_sample_csv():
    sample_data = {
        "Date": ["2023-09-01", "2023-09-02", "2023-09-03", "2023-09-04"],
        "Landing Page": ["/test-page-1", "/test-page-2", "/control-page-1", "/control-page-2"],
        "Url Clicks": [100, 150, 200, 120],
        "Impressions": [1000, 1200, 1500, 1100]
    }
    sample_df = pd.DataFrame(sample_data)
    return sample_df

# Function to allow CSV download
def convert_df_to_csv(df):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

# Helper functions
def filter_by_regex(data, regex):
    return data[data['Landing Page'].str.contains(regex, na=False, flags=re.IGNORECASE)]

def filter_by_date(data, start_date, end_date):
    # Ensure both start_date and end_date are pandas Timestamp objects
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    return data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]

def calculate_differences(current, previous):
    absolute_diff = current - previous
    relative_diff = (absolute_diff / previous * 100) if previous != 0 else None
    return absolute_diff, relative_diff

# Streamlit interface
st.title("GSC Page Group Analysis")
st.markdown("Export the GSC data in the right format from [here](https://lookerstudio.google.com/u/0/reporting/7d53bdfb-263d-484d-a959-0d9205eaf2e2/page/hiLGE/edit). Just ensure you have enough data to cover the pre and post change date range! Upload the exported CSV below to proceed.")

# Add a button to download the sample CSV
sample_df = create_sample_csv()
csv_data = convert_df_to_csv(sample_df)
st.markdown("For this to work, the format of the CSV file needs to be exactly as anticipated, click download below to see an example of the format provided. The date must be yyyy-mm-dd format!")
st.download_button(label="Download Sample CSV", data=csv_data, file_name='sample_gsc_data.csv', mime='text/csv')

# Upload CSV file
uploaded_file = st.file_uploader("Upload GSC CSV", type="csv")
if uploaded_file is not None:
    # Read CSV into a DataFrame
    data = pd.read_csv(uploaded_file)

    # Ensure there's a 'Date' column and convert to datetime
    if 'Date' not in data.columns:
        st.error("The CSV file must contain a 'Date' column with daily data.")
    else:
        # Convert 'Date' column to datetime with error handling
        data['Date'] = pd.to_datetime(data['Date'], format='%Y-%m-%d', errors='coerce')
        
        # Check for NaT values in 'Date'
        if data['Date'].isnull().any():
            st.warning("There are invalid dates in the 'Date' column. These will be marked as NaT. Please check all dates are yyyy-mm-dd format.")
            st.write(data[data['Date'].isnull()])
    
    # Convert Url Clicks and Impressions to numeric for easier handling
    data['Url Clicks'] = pd.to_numeric(data['Url Clicks'], errors='coerce')
    data['Impressions'] = pd.to_numeric(data['Impressions'], errors='coerce')
    
    # User inputs for deployment date range and regex
    test_regex = st.text_input("Enter regex for Test group", "")
    control_regex = st.text_input("Enter regex for Control group (optional) - Leave blank to compare against all page performance.", "")
    
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
            # Exclude the test group from the control group
            control_group = data[~data.index.isin(test_group.index)]
        
        # Filter data by pre-test period and previous year period
        test_pre_test = filter_by_date(test_group, pre_test_start, pre_test_end)
        test_prev_year = filter_by_date(test_group, prev_year_test_start, prev_year_test_end)
        control_pre_test = filter_by_date(control_group, pre_test_start, pre_test_end)
        control_prev_year = filter_by_date(control_group, prev_year_test_start, prev_year_test_end)

        # Filter data by test period
        test_period = filter_by_date(test_group, test_start, test_end)
        control_period = filter_by_date(control_group, test_start, test_end)

        # Summary Statistics
        # 1. Number of days in each period (check data completeness)
        num_days_test_period = (test_period['Date'].nunique())
        num_days_pre_test_period = (test_pre_test['Date'].nunique())
        num_days_yoy_period = (test_prev_year['Date'].nunique())

        # 2. Unique pages in each period
        unique_pages_test_period = test_period['Landing Page'].nunique()
        unique_pages_pre_test_period = test_pre_test['Landing Page'].nunique()
        unique_pages_yoy_period = test_prev_year['Landing Page'].nunique()

        st.subheader("Summary Statistics")
        st.write(f"**Number of days in Test Period**: {num_days_test_period}")
        st.write(f"**Number of days in Pre-Test Period**: {num_days_pre_test_period}")
        st.write(f"**Number of days in YoY Period**: {num_days_yoy_period}")

        st.write(f"**Unique Pages in Test Period**: {unique_pages_test_period}")
        st.write(f"**Unique Pages in Pre-Test Period**: {unique_pages_pre_test_period}")
        st.write(f"**Unique Pages in YoY Period**: {unique_pages_yoy_period}")

        # Sum metrics for each period (test, pre-test, and previous year)
        test_metrics_pre_test = test_pre_test[['Url Clicks', 'Impressions']].sum()
        test_metrics_prev_year = test_prev_year[['Url Clicks', 'Impressions']].sum()
        control_metrics_pre_test = control_pre_test[['Url Clicks', 'Impressions']].sum()
        control_metrics_prev_year = control_prev_year[['Url Clicks', 'Impressions']].sum()

        test_metrics_test_period = test_period[['Url Clicks', 'Impressions']].sum()
        control_metrics_test_period = control_period[['Url Clicks', 'Impressions']].sum()

        # Calculate differences for test and control groups
        test_differences = []
        control_differences = []
        rel_diff_test_pre = {}
        rel_diff_test_yoy = {}
        rel_diff_control_pre = {}
        rel_diff_control_yoy = {}

        for metric in ['Url Clicks', 'Impressions']:
            # Test Group: test vs pre-test, and test vs previous year
            abs_diff_test_pre, rel_diff_test_pre[metric] = calculate_differences(test_metrics_test_period[metric], test_metrics_pre_test[metric])
            abs_diff_test_yoy, rel_diff_test_yoy[metric] = calculate_differences(test_metrics_test_period[metric], test_metrics_prev_year[metric])

            test_differences.append({
                "Metric": metric,
                "Test Group Absolute Difference (vs Pre-Test)": abs_diff_test_pre,
                "Test Group Relative Difference (vs Pre-Test) (%)": rel_diff_test_pre[metric],
                "Test Group Absolute Difference (vs YoY)": abs_diff_test_yoy,
                "Test Group Relative Difference (vs YoY) (%)": rel_diff_test_yoy[metric]
            })

            # Control Group: test vs pre-test, and test vs previous year
            abs_diff_control_pre, rel_diff_control_pre[metric] = calculate_differences(control_metrics_test_period[metric], control_metrics_pre_test[metric])
            abs_diff_control_yoy, rel_diff_control_yoy[metric] = calculate_d
