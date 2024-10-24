import streamlit as st
import pandas as pd
import re
import logging
from datetime import timedelta
from io import StringIO
from scipy.stats import ttest_ind

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
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    filtered_data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
    
    # DEBUG: Log the number of rows filtered
    logging.info(f"Filtered {len(filtered_data)} rows between {start_date} and {end_date}")
    return filtered_data

def calculate_differences(current, previous):
    absolute_diff = current - previous
    relative_diff = (absolute_diff / previous * 100) if previous != 0 else None
    return absolute_diff, relative_diff

# Function for color-coding the results
def colorize_diff(diff):
    if diff > 0:
        return f"<span style='color: green;'>+{diff:.2f}%</span>"
    elif diff < 0:
        return f"<span style='color: red;'>{diff:.2f}%</span>"
    else:
        return "<span style='color: black;'>0.00%</span>"

# Function to calculate p-value between two samples
def calculate_p_value(sample1, sample2):
    stat, p_value = ttest_ind(sample1, sample2, equal_var=False)  # Welch's t-test
    return p_value

# Streamlit interface
st.title("GSC Page Group Analysis")

# Add a button to download the sample CSV
sample_df = create_sample_csv()
csv_data = convert_df_to_csv(sample_df)
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
        
        # DEBUG: Log any rows with invalid dates
        if data['Date'].isnull().any():
            st.warning("Invalid dates found. Please check the 'Date' column format (yyyy-mm-dd).")
            logging.error(f"Invalid dates in rows: {data[data['Date'].isnull()]}")
    
    # Convert Url Clicks and Impressions to numeric for easier handling
    data['Url Clicks'] = pd.to_numeric(data['Url Clicks'], errors='coerce')
    data['Impressions'] = pd.to_numeric(data['Impressions'], errors='coerce')
    
    # User inputs for deployment date range and regex
    test_regex = st.text_input("Enter regex for Test group", "")
    control_regex = st.text_input("Enter regex for Control group (optional)", "")
    
    # Select test date range
    test_start = st.date_input("Test Start Date")
    test_end = st.date_input("Test End Date")
    
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
        
        # Filter data by pre-test and previous year periods
        test_pre_test = filter_by_date(test_group, pre_test_start, pre_test_end)
        test_prev_year = filter_by_date(test_group, prev_year_test_start, prev_year_test_end)

        control_pre_test = filter_by_date(control_group, pre_test_start, pre_test_end)
        control_prev_year = filter_by_date(control_group, prev_year_test_start, prev_year_test_end)

        # Filter data by test period
        test_period = filter_by_date(test_group, test_start, test_end)
        control_period = filter_by_date(control_group, test_start, test_end)

        # Count unique pages in each period
        unique_pages_test = test_period['Landing Page'].nunique()
        unique_pages_pre_test = test_pre_test['Landing Page'].nunique()
        unique_pages_yoy = test_prev_year['Landing Page'].nunique()

        # Sum metrics for each period
        test_metrics_test_period = test_period[['Url Clicks', 'Impressions']].sum()
        test_metrics_pre_test = test_pre_test[['Url Clicks', 'Impressions']].sum()
        test_metrics_prev_year = test_prev_year[['Url Clicks', 'Impressions']].sum()

        control_metrics_test_period = control_period[['Url Clicks', 'Impressions']].sum()
        control_metrics_pre_test = control_pre_test[['Url Clicks', 'Impressions']].sum()
        control_metrics_prev_year = control_prev_year[['Url Clicks', 'Impressions']].sum()

        # Calculate differences
        clicks_diff, clicks_yoy = calculate_differences(test_metrics_test_period['Url Clicks'], test_metrics_pre_test['Url Clicks'])
        impressions_diff, impressions_yoy = calculate_differences(test_metrics_test_period['Impressions'], test_metrics_pre_test['Impressions'])

        # Calculate p-values for test and control groups
        p_value_clicks_test_pre = calculate_p_value(test_period['Url Clicks'], test_pre_test['Url Clicks'])
        p_value_clicks_yoy = calculate_p_value(test_period['Url Clicks'], test_prev_year['Url Clicks'])
        
        p_value_control_clicks_pre = calculate_p_value(control_period['Url Clicks'], control_pre_test['Url Clicks'])
        p_value_control_clicks_yoy = calculate_p_value(control_period['Url Clicks'], control_prev_year['Url Clicks'])

        # Display summary with color-coding
        st.subheader("Test Group Metrics Summary")
        st.markdown(f"**Url Clicks**: {test_metrics_test_period['Url Clicks']} (Diff: {colorize_diff(clicks_diff)}, YoY: {colorize_diff(clicks_yoy)})", unsafe_allow_html=True)
        st.markdown(f"**P-value for Clicks (Test vs Pre-test)**: {p_value_clicks_test_pre:.5f}")
        st.markdown(f"**P-value for Clicks (Test vs YoY)**: {p_value_clicks_yoy:.5f}")
        
        st.markdown(f"**Impressions**: {test_metrics_test_period['Impressions']} (Diff: {colorize_diff(impressions_diff)}, YoY: {colorize_diff(impressions_yoy)})", unsafe_allow_html=True)

        st.subheader("Control Group Metrics Summary")
        st.markdown(f"**Url Clicks**: {control_metrics_test_period['Url Clicks']}")
        st.markdown(f"**P-value for Clicks (Control vs Pre-test)**: {p_value_control_clicks_pre:.5f}")
        st.markdown(f"**P-value for Clicks (Control vs YoY)**: {p_value_control_clicks_yoy:.5f}")
