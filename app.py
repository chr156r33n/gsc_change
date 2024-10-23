# Count of unique pages and number of days for the given period
def count_unique_pages_and_days(data, start_date, end_date):
    filtered_data = filter_by_date(data, start_date, end_date)
    unique_pages = filtered_data['Landing Page'].nunique()
    num_days = len(filtered_data['Date'].unique())
    return unique_pages, num_days

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

        # Summary of number of unique pages and days for each period in the test group
        test_unique_pages_test, test_days_test = count_unique_pages_and_days(test_group, test_start, test_end)
        test_unique_pages_pre, test_days_pre = count_unique_pages_and_days(test_group, pre_test_start, pre_test_end)
        test_unique_pages_yoy, test_days_yoy = count_unique_pages_and_days(test_group, prev_year_test_start, prev_year_test_end)

        # Display these new statistics
        st.subheader("Test Group Summary")
        st.write(f"**Number of days** in Test period: {test_days_test}, Pre-test period: {test_days_pre}, YoY period: {test_days_yoy}")
        st.write(f"**Unique pages** in Test period: {test_unique_pages_test}, Pre-test period: {test_unique_pages_pre}, YoY period: {test_unique_pages_yoy}")

        # Proceed with the rest of your analysis as it was.
