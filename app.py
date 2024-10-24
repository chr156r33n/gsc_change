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

        # Sum metrics for each period (test, pre-test, and previous year)
        test_metrics_pre_test = test_pre_test[['Url Clicks', 'Impressions']].sum()
        test_metrics_prev_year = test_prev_year[['Url Clicks', 'Impressions']].sum()
        control_metrics_pre_test = control_pre_test[['Url Clicks', 'Impressions']].sum()
        control_metrics_prev_year = control_prev_year[['Url Clicks', 'Impressions']].sum()
        
        # Filter data by test period
        test_period = filter_by_date(test_group, test_start, test_end)
        test_metrics_test_period = test_period[['Url Clicks', 'Impressions']].sum()
        control_period = filter_by_date(control_group, test_start, test_end)
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
            abs_diff_control_yoy, rel_diff_control_yoy[metric] = calculate_differences(control_metrics_test_period[metric], control_metrics_prev_year[metric])

            control_differences.append({
                "Metric": metric,
                "Control Group Absolute Difference (vs Pre-Test)": abs_diff_control_pre,
                "Control Group Relative Difference (vs Pre-Test) (%)": rel_diff_control_pre[metric],
                "Control Group Absolute Difference (vs YoY)": abs_diff_control_yoy,
                "Control Group Relative Difference (vs YoY) (%)": rel_diff_control_yoy[metric]
            })
        
        # Summary of key results
        st.subheader("Summary of Results")

        def color_metric(value):
            if value > 0:
                return f"<span style='color:green'>{value:.2f}%</span>"
            elif value < 0:
                return f"<span style='color:red'>{value:.2f}%</span>"
            else:
                return f"<span>{value:.2f}%</span>"

        # Function to calculate p-value between two samples
        def calculate_p_value(sample1, sample2):
            stat, p_value = ttest_ind(sample1, sample2, equal_var=False)  # Welch's t-test
            return p_value
        # Calculate p-values for test and control groups
        p_value_clicks_test_pre = calculate_p_value(test_period['Url Clicks'], test_pre_test['Url Clicks'])
        p_value_clicks_yoy = calculate_p_value(test_period['Url Clicks'], test_prev_year['Url Clicks'])

        p_value_control_clicks_pre = calculate_p_value(control_period['Url Clicks'], control_pre_test['Url Clicks'])
        p_value_control_clicks_yoy = calculate_p_value(control_period['Url Clicks'], control_prev_year['Url Clicks'])

        
        # Test group summary
        st.write("### Test Group")
        st.markdown("For us to be confident the test has led to an improvement, we'd expect some levels of improvement in period on period or year over year AND that improvement to be above the control group. If traffic to the test pages is impacted by seasonality and/or sales, then pre-test vs post-test may not give accurate findings. Year over year should be considered if the test pages are comparable against the previous year. If you're confident it is a fair comparison, then a positive YoY figure is a good sign.")
        
        st.write(f"##### **Clicks:** Test period: {test_metrics_test_period['Url Clicks']:,}, "
                 f"Pre-test: {test_metrics_pre_test['Url Clicks']:,} "
                 f"({color_metric(rel_diff_test_pre['Url Clicks'])}), "
                 f"YoY: {test_metrics_prev_year['Url Clicks']:,} "
                 f"({color_metric(rel_diff_test_yoy['Url Clicks'])}).", unsafe_allow_html=True)
        
        st.write(f"##### **Impressions:** Test period: {test_metrics_test_period['Impressions']:,}, "
                 f"Pre-test: {test_metrics_pre_test['Impressions']:,} "
                 f"({color_metric(rel_diff_test_pre['Impressions'])}), "
                 f"YoY: {test_metrics_prev_year['Impressions']:,} "
                 f"({color_metric(rel_diff_test_yoy['Impressions'])}).", unsafe_allow_html=True)
        
        # Control group summary
        st.write("### Control Group")
        st.markdown("The control group change is important because we _didn't_ make a change to these URLs. Therefore, any change in performance here would – we'd expect – be different from the test group. If the control group is out-performing the test, we can assume that the test was less likely to be positive. If the control is under-performing the test, it could mean that the test changes were positive. If the two values are broadly the same, then conclusions could be less sure.")
        
        st.write(f"##### **Clicks:** Test period: {control_metrics_test_period['Url Clicks']:,},\n\n "
                 f"Pre-test: {control_metrics_pre_test['Url Clicks']:,} \n\n"
                 f"({color_metric(rel_diff_control_pre['Url Clicks'])}), \n\n"
                 f"YoY: {control_metrics_prev_year['Url Clicks']:,} \n\n"
                 f"({color_metric(rel_diff_control_yoy['Url Clicks'])}).", unsafe_allow_html=True)
        
        st.write(f"##### **Impressions:** Test period: {control_metrics_test_period['Impressions']:,}, \n\n"
                 f"Pre-test: {control_metrics_pre_test['Impressions']:,} \n\n"
                 f"({color_metric(rel_diff_control_pre['Impressions'])}), \n\n"
                 f"YoY: {control_metrics_prev_year['Impressions']:,} \n\n"
                 f"({color_metric(rel_diff_control_yoy['Impressions'])}).", unsafe_allow_html=True)

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

        # NEW: Display the filtered data for debugging
        st.write("### Understand Your Data")
        st.markdown("Some extra information to help understand the comparison periods, check you have the right amount of days in the data etc.")
                    
        st.write("#### Test Group URLs")
        st.write("Ensure that only the URLs you want to test are in here. If there are URLs you don't expect, it is likely the regex is wrong.")
        st.write(test_period)
        st.write("#### Control Group URLs")
        st.write("If URLs in the control group are super-different to URLs in the test group the validity of the comparison may diminish.")
        st.write(control_period)
        
        # Count the number of days in each period
        num_days_test_period = len(test_period['Date'].unique())
        num_days_pre_test_period = len(test_pre_test['Date'].unique())
        num_days_yoy_period = len(test_prev_year['Date'].unique())

        # Count unique pages in each period
        unique_pages_test = test_period['Landing Page'].nunique()
        unique_pages_pre_test = test_pre_test['Landing Page'].nunique()
        unique_pages_yoy = test_prev_year['Landing Page'].nunique()

        # Display counts to debug
        st.write("#### Number of Days")
        st.write(f"Number of days in the test period: {num_days_test_period}")
        st.write(f"Number of days in the pre-test period: {num_days_pre_test_period}")
        st.write(f"Number of days in the YoY period: {num_days_yoy_period}")

        st.write("#### Number of Unique Pages")
        st.write(f"Unique pages in the test period: {unique_pages_test}")
        st.write(f"Unique pages in the pre-test period: {unique_pages_pre_test}")
        st.write(f"Unique pages in the YoY period: {unique_pages_yoy}")

        # Test group
        st.markdown(f"**P-value for Clicks (Test vs Pre-test)**: {p_value_clicks_test_pre:.5f}")
        st.markdown(f"**P-value for Clicks (Test vs YoY)**: {p_value_clicks_yoy:.5f}")
        
        # Control group
        st.markdown(f"**P-value for Clicks (Control vs Pre-test)**: {p_value_control_clicks_pre:.5f}")
        st.markdown(f"**P-value for Clicks (Control vs YoY)**: {p_value_control_clicks_yoy:.5f}")
        
