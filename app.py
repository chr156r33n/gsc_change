import streamlit as st
import pandas as pd
import re
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to filter URLs by regex pattern
def filter_by_regex(data, pattern):
    return data[data['Landing Page'].apply(lambda x: bool(re.search(pattern, x)))]

# Function to calculate absolute and relative difference
def calculate_differences(metric_current, metric_previous):
    abs_diff = metric_current - metric_previous
    if metric_previous != 0:
        rel_diff = (abs_diff / metric_previous) * 100
    else:
        rel_diff = float('nan')
    return abs_diff, rel_diff

# Function to filter data by date range
def filter_by_date(data, start_date, end_date):
    mask = (data['Date'] >= pd.to_datetime(start_date)) & (data['Date'] <= pd.to_datetime(end_date))
    return data.loc[mask]

# Streamlit interface
st.title("GSC Page Group Analysis")
st.markdown("Export the GSC data in the right format from [here](https://lookerstudio.google.com/u/0/reporting/7d53bdfb-263d-484d-a959-0d9205eaf2e2/page/hiLGE/edit). Just ensure you have enough data to cover the pre and post change date range! Upload the exported CSV below to proceed.")

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

        # Sum metrics for pre-test and previous year periods
        test_metrics_pre_test = test_pre_test[['Url Clicks', 'Impressions']].sum()
        test_metrics_prev_year = test_prev_year[['Url Clicks', 'Impressions']].sum()
        
        control_metrics_pre_test = control_pre_test[['Url Clicks', 'Impressions']].sum()
        control_metrics_prev_year = control_prev_year[['Url Clicks', 'Impressions']].sum()

        # Filter data by test period
        test_period = filter_by_date(test_group, test_start, test_end)
        test_metrics_test_period = test_period[['Url Clicks', 'Impressions']].sum()

        control_period = filter_by_date(control_group, test_start, test_end)
        control_metrics_test_period = control_period[['Url Clicks', 'Impressions']].sum()

        # Calculate clicks and impressions per day
        test_clicks_per_day_test = round(test_metrics_test_period['Url Clicks'] / len(test_period), 2)
        test_impressions_per_day_test = round(test_metrics_test_period['Impressions'] / len(test_period), 2)

        test_clicks_per_day_pre_test = round(test_metrics_pre_test['Url Clicks'] / len(test_pre_test), 2)
        test_impressions_per_day_pre_test = round(test_metrics_pre_test['Impressions'] / len(test_pre_test), 2)

        test_clicks_per_day_prev_year = round(test_metrics_prev_year['Url Clicks'] / len(test_prev_year), 2)
        test_impressions_per_day_prev_year = round(test_metrics_prev_year['Impressions'] / len(test_prev_year), 2)

        control_clicks_per_day_test = round(control_metrics_test_period['Url Clicks'] / len(control_period), 2)
        control_impressions_per_day_test = round(control_metrics_test_period['Impressions'] / len(control_period), 2)

        control_clicks_per_day_pre_test = round(control_metrics_pre_test['Url Clicks'] / len(control_pre_test), 2)
        control_impressions_per_day_pre_test = round(control_metrics_pre_test['Impressions'] / len(control_pre_test), 2)

        control_clicks_per_day_prev_year = round(control_metrics_prev_year['Url Clicks'] / len(control_prev_year), 2)
        control_impressions_per_day_prev_year = round(control_metrics_prev_year['Impressions'] / len(control_prev_year), 2)

        # Display aggregate clicks and impressions for each period, including per day metrics
        st.subheader("Aggregate Clicks and Impressions by Period (Test Group)")

        st.write("**Test Group - Test Period**")
        st.write(test_metrics_test_period.round(2))
        st.write(f"Clicks per day: {test_clicks_per_day_test}, Impressions per day: {test_impressions_per_day_test}")

        st.write("**Test Group - Pre-Test Period**")
        st.write(test_metrics_pre_test.round(2))
        st.write(f"Clicks per day: {test_clicks_per_day_pre_test}, Impressions per day: {test_impressions_per_day_pre_test}")

        st.write("**Test Group - Last Year's Test Period**")
        st.write(test_metrics_prev_year.round(2))
        st.write(f"Clicks per day: {test_clicks_per_day_prev_year}, Impressions per day: {test_impressions_per_day_prev_year}")

        st.subheader("Aggregate Clicks and Impressions by Period (Control Group)")

        st.write("**Control Group - Test Period**")
        st.write(control_metrics_test_period.round(2))
        st.write(f"Clicks per day: {control_clicks_per_day_test}, Impressions per day: {control_impressions_per_day_test}")

        st.write("**Control Group - Pre-Test Period**")
        st.write(control_metrics_pre_test.round(2))
        st.write(f"Clicks per day: {control_clicks_per_day_pre_test}, Impressions per day: {control_impressions_per_day_pre_test}")

        st.write("**Control Group - Last Year's Test Period**")
        st.write(control_metrics_prev_year.round(2))
        st.write(f"Clicks per day: {control_clicks_per_day_prev_year}, Impressions per day: {control_impressions_per_day_prev_year}")
