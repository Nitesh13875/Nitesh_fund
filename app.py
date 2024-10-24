import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib_venn import venn2

ACCESS_TOKEN = "RvAEWi1UeKNRy9mONhee8jMjJr97"

def home():
    def load_data(file_path):
        try:
            data = pd.read_csv(file_path)
            data['isin'] = data['isin'].astype(str)
            data['scheme_name'] = data['scheme_name'].astype(str)
            data['scheme_code'] = data['scheme_code'].astype(str)
            data['ID'] = data['ID'].astype(str)
            return data
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return None

    def search_data(data, user_input):
        if user_input:
            filtered_data = data[
                data['isin'].str.contains(user_input, case=False, na=False) |
                data['scheme_name'].str.contains(user_input, case=False, na=False) |
                data['scheme_code'].str.contains(user_input, case=False, na=False) |
                data['ID'].str.contains(user_input, case=False, na=False)
            ]
            return filtered_data
        return pd.DataFrame()  # Return an empty DataFrame if no input

    def fetch_fund_details(selected_id):
        api_url = f"https://api-global.morningstar.com/sal-service/v1/fund/quote/v3/{selected_id}/data?fundServCode=&showAnalystRatingChinaFund=false&showAnalystRating=false&languageId=en&locale=en&clientId=RSIN_SAL&benchmarkId=mstarorcat&component=sal-mip-quote&version=4.13.0&access_token={ACCESS_TOKEN}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Error fetching fund details: {e}")
            return {}

    def fetch_risk_data(selected_id, selected_year):
        api_url = f"https://api-global.morningstar.com/sal-service/v1/fund/performance/riskVolatility/{selected_id}/data?currency=&longestTenure=false&languageId=en&locale=en&clientId=RSIN_SAL&benchmarkId=mstarorcat&component=sal-mip-risk-volatility-measures&version=4.13.0&access_token={ACCESS_TOKEN}"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"Error fetching risk data: {e}")
            return {}

    def fetch_nav_history(scheme_code,scheme_name):
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            st.error(f"Error fetching data for Scheme Code: {scheme_code}")
            return []

    def get_closest_nav(nav_data, target_date):
        nav_data_sorted = sorted(nav_data, key=lambda x: datetime.strptime(x['date'], '%d-%m-%Y'), reverse=True)
        for entry in nav_data_sorted:
            nav_date = datetime.strptime(entry['date'], '%d-%m-%Y')
            if nav_date <= target_date:
                return float(entry['nav'])
        return None

    def calculate_returns(nav_data):
        today = datetime.today()
        periods = {
            '1_year': today - timedelta(days=365),
            '3_year': today - timedelta(days=365 * 3),
            '5_year': today - timedelta(days=365 * 5)
        }
        required_days = {'1_year': 230, '3_year': 700, '5_year': 1200}
        try:
            nav_today = float(nav_data[0]['nav'])  # Latest NAV (Assuming sorted)
        except (IndexError, ValueError):
            return None, None, None

        returns = {}
        for period, date in periods.items():
            nav_past = get_closest_nav(nav_data, date)
            if nav_past:
                returns[period] = ((nav_today / nav_past) - 1) * 100
            else:
                returns[period] = None

            trading_days = sum(1 for entry in nav_data if datetime.strptime(entry['date'], '%d-%m-%Y') >= date)
            if trading_days < required_days[period]:
                returns[period] = None

        return round(returns['1_year'], 2) if returns['1_year'] is not None else None, \
            round(returns['3_year'], 2) if returns['3_year'] is not None else None, \
            round(returns['5_year'], 2) if returns['5_year'] is not None else None

    def display_fund_details(fund_data):
        if fund_data:
            st.write("Fund Details:")
            st.table({
                'Fund Name': [fund_data.get('investmentName', None)],
                'Prospectus Benchmark': [fund_data.get('prospectusBenchmarkName', None)],
                'Expense Ratio': [fund_data.get('expenseRatio', None)],
                'Last Turnover Ratio': [fund_data.get('lastTurnoverRatio', None)],
                'Equity Style Box': [fund_data.get('equityStyleBox', None)],
                'Load': [fund_data.get('load', None)],
                'NAV': [fund_data.get('nav', None)]
            })
        else:
            st.write("No fund details available.")
    def display_risk_data(risk_data, selected_year):
        if risk_data and isinstance(risk_data, dict):
            # Extracting risk and volatility information for the selected year
            risk_info = risk_data.get('fundRiskVolatility', {}).get(f'for{selected_year.replace(" ", "")}', {})
            category_info = risk_data.get('categoryRiskVolatility', {}).get(f'for{selected_year.replace(" ", "")}', {})
            index_info = risk_data.get('indexRiskVolatility', {}).get(f'for{selected_year.replace(" ", "")}', {})
            
            # Ensure index_info is a dictionary to avoid AttributeError
            if index_info is None:
                index_info = {}

            # Create a structured DataFrame to hold the data
            structured_data = pd.DataFrame({
                'Investment': [
                    risk_info.get('alpha', 'Data not available'),
                    risk_info.get('beta', 'Data not available'),
                    risk_info.get('rSquared', 'Data not available'),
                    risk_info.get('standardDeviation', 'Data not available'),
                    risk_info.get('sharpeRatio', 'Data not available'),
                ],
                'Category': [
                    category_info.get('alpha', 'Data not available'),
                    category_info.get('beta', 'Data not available'),
                    category_info.get('rSquared', 'Data not available'),
                    category_info.get('standardDeviation', 'Data not available'),
                    category_info.get('sharpeRatio', 'Data not available'),
                ],
                'Index': [
                    index_info.get('alpha', 'Data not available'),
                    index_info.get('beta', 'Data not available'),
                    index_info.get('rSquared', 'Data not available'),
                    index_info.get('standardDeviation', 'Data not available'),
                    index_info.get('sharpeRatio', 'Data not available'),
                ]
            }, index=["Alpha", "Beta", "Standard Deviation", "Sharpe Ratio", "rSquared"])

            # Display the DataFrame in the Streamlit app
            st.write(f"Risk and Volatility Data for {selected_year}:")
            st.dataframe(structured_data)
        else:
            st.write("No risk data available.")

    # Function to plot historical NAV data
    def plot_nav_history(nav_data,scheme_name):
        st.write("Historical NAV Chart ")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[datetime.strptime(nav['date'], '%d-%m-%Y') for nav in nav_data],
            y=[float(nav['nav']) for nav in nav_data],
            mode='lines',
            name='NAV',
            line=dict(color='#00CC96', width=3),  # Bright green line for trading look
            hovertemplate='<b>Date</b>: %{x|%d-%m-%Y}<br><b>NAV</b>: %{y}<extra></extra>',  # Enhanced hover info
        ))
        # Add layout for a more trading-style look

        fig.update_layout(

            title=f"Historical NAV for {scheme_name}",
            xaxis_title="Date",
            yaxis_title="NAV",
            xaxis=dict(
                showline=True, showgrid=True, gridcolor='#444',  # Axis lines and gridlines
                tickformat='%d-%m-%Y',  # Ensure full date with day is displayed
                linecolor='white',  # Axis line color
                ticks='outside',
                tickwidth=2,
                ticklen=10,
                tickcolor='white',
            ),
            yaxis=dict(
                showline=True, showgrid=True, gridcolor='#444',  # Grid and axis lines on Y-axis
                linecolor='white',
                ticks='outside',
                tickwidth=2,
                ticklen=10,
                tickcolor='white',
            ),
            margin=dict(l=30, r=30, t=30, b=30),
            height=500,
            plot_bgcolor='black',  # Black background for trading look
            paper_bgcolor='black',  # Outer background
            font=dict(color='white'),  # White text
            hoverlabel=dict(
                bgcolor="black",  # Black background for hover box
                font_size=13,
                font_family="Arial",
                bordercolor="white",
                font_color="white",
            ),
            title_x=0.5,  # Center the title
        )

        # Display the plot in the center of the page with a box style
        st.plotly_chart(fig, use_container_width=True)

    # Main application logic
    def main():
        st.title("Mutual Fund Data Search")
        data = load_data('data.csv')

        # User input
        user_input = st.text_input("Enter ISIN, Scheme Name, Scheme Code, or ID:")
        result = search_data(data, user_input)

        if not result.empty:
            st.write("Matching Results:")
            st.table(result[['scheme_name', 'isin', 'scheme_code', 'ID']])
            # Assuming the user selects a row, fetch the ID and corresponding scheme code
            selected_row = result.iloc[0]  # Get the first matching result
            selected_id = selected_row['ID']
            selected_scheme_code = selected_row['scheme_code']
            selected_scheme_name = selected_row['scheme_name']  # Get the scheme code from the DataFrame

            # Fetch fund details
            fund_data = fetch_fund_details(selected_id)
            display_fund_details(fund_data)
            st.write(f"Details for {selected_scheme_name} (Scheme Code: {selected_scheme_code})")

            # Fetch NAV history and calculate returns
            nav_data = fetch_nav_history(selected_scheme_code,selected_scheme_name)
            if nav_data:
                plot_nav_history(nav_data,selected_scheme_name)
                returns = calculate_returns(nav_data)
                
                # Create a DataFrame to hold the calculated returns
                returns_df = pd.DataFrame({
                    'Period': ['1 Year', '3 Years', '5 Years'],
                    'Return (%)': [returns[0], returns[1], returns[2]]
                })
                st.write("Calculated Returns:")
                st.dataframe(returns_df)

            else:
                st.write("No matching results found.")

            # Dropdown to select the year
            selected_year = st.selectbox("Select Year for Risk Analysis", ["1 Year", "3 Years", "5 Years"])
            
            # Fetch risk data
            risk_data = fetch_risk_data(selected_id, selected_year)
            display_risk_data(risk_data, selected_year)

            

    
    if __name__ == "__main__":
        main()


def Holdings():
 

    # Set the title of the app
    st.title("Mutual Fund Holdings Viewer")

    # Create a text input for the user to enter the fund ID
    fund_id = st.text_input("Enter Fund ID:", placeholder="Example: F00000PDC9")

    if st.button("Fetch Holdings Data"):
        if fund_id:
            # Construct the API URL
            url = f"https://api-global.morningstar.com/sal-service/v1/fund/portfolio/holding/v2/{fund_id}/data?premiumNum=100&freeNum=25&hideesg=true&languageId=en&locale=en&clientId=RSIN_SAL&benchmarkId=mstarorcat&component=sal-mip-holdings&version=4.31.0&access_token={ACCESS_TOKEN}"
            # Fetch the data from the API
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()

                # Extract relevant information
                masterPortfolioId = data.get('masterPortfolioId')
                secId = data.get('secId')
                holdingSummary = data.get('holdingSummary', {})
                equityHoldings = data.get('equityHoldingPage', {}).get('holdingList', [])

                # Display fund information in a table without index
                st.subheader("Fund Information")
                fund_info = {
                    "Master Portfolio ID": masterPortfolioId,
                    "Security ID": secId,
                    "Portfolio Date": holdingSummary.get('portfolioDate'),
                    "Total Number of Holdings": holdingSummary.get('numberOfHolding'),
                    "Equity Holdings": holdingSummary.get('equityNumberOfHolding'),
                    "Average Turnover Ratio": f"{holdingSummary.get('averageTurnoverRatio')}%",
                    "Last Turnover": f"{holdingSummary.get('lastTurnover')}% on {holdingSummary.get('LastTurnoverDate')}"
                }
                st.table(pd.DataFrame(fund_info.items(), columns=["Field", "Value"]).set_index("Field"))

                # Create a DataFrame for equity holdings
                if equityHoldings:
                    holdings_df = pd.DataFrame(equityHoldings)

                    # Set index to start from 1
                    holdings_df.index += 1  # This shifts the index to start from 1

                    # Display holdings data
                    st.subheader("Equity Holdings")
                    st.dataframe(holdings_df[['isin', 'securityName', 'weighting', 'numberOfShare', 'marketValue', 'country', 'ticker', 'totalReturn1Year', 'sector']])
                    st.write("### Holding Weighting Distribution")
                    
                    # Pie chart for holdings weighting distribution
                    plt.figure(figsize=(12, 8))  # Increase figure size
                    # Abbreviate security names for better visibility
                    short_names = [name if len(name) <= 10 else name[:10] + '..' for name in holdings_df['securityName']]
                    explode = [0.1] * len(holdings_df)
                    plt.pie(holdings_df['weighting'], labels=short_names, autopct='%1.1f%%', startangle=140, 
                            pctdistance=0.90, textprops={'fontsize': 6}, explode=explode)
                    # Draw a circle at the center of pie to make it look like a donut
                    centre_circle = plt.Circle((0, 0), 0.65, fc='white')
                    fig = plt.gcf()
                    fig.gca().add_artist(centre_circle)
                    st.pyplot(fig)

                    # Sector-wise distribution chart
                    st.write("### Sector-wise Distribution")
                    sector_distribution = holdings_df['sector'].value_counts()
                    plt.figure(figsize=(10, 5))
                    sector_distribution.plot(kind='bar', color='skyblue')
                    plt.title('Equity Holdings Sector Distribution')
                    plt.xlabel('Sector')
                    plt.ylabel('Number of Holdings')
                    st.pyplot(plt)
                else:
                    st.write("No equity holdings found for this fund ID.")
            else:
                st.error(f"Failed to fetch data for ID {fund_id}: {response.status_code}")
        else:
            st.warning("Please enter a Fund ID to fetch data.")

    # Comparison section
    st.write("---")
    st.subheader("Fund Overlap Analysis")
    compare = st.checkbox("Do you want to compare two funds?")

    if compare:
        fund_id_1 = st.text_input("Enter First Fund ID:", placeholder="Example: F00000PDC9")
        fund_id_2 = st.text_input("Enter Second Fund ID:", placeholder="Example: F00000PDC9")

        # Add a button to initiate the comparison
        if st.button("Compare Holdings"):
            if fund_id_1 and fund_id_2:
                # Fetch data for both funds
                response_1 = requests.get(f"https://api-global.morningstar.com/sal-service/v1/fund/portfolio/holding/v2/{fund_id_1}/data?premiumNum=100&freeNum=25&hideesg=true&languageId=en&locale=en&clientId=RSIN_SAL&benchmarkId=mstarorcat&component=sal-mip-holdings&version=4.31.0&access_token=iTP1tjYXA0gMrzvFpIK00wZ9m0b4")
                response_2 = requests.get(f"https://api-global.morningstar.com/sal-service/v1/fund/portfolio/holding/v2/{fund_id_2}/data?premiumNum=100&freeNum=25&hideesg=true&languageId=en&locale=en&clientId=RSIN_SAL&benchmarkId=mstarorcat&component=sal-mip-holdings&version=4.31.0&access_token=iTP1tjYXA0gMrzvFpIK00wZ9m0b4")

                if response_1.status_code == 200 and response_2.status_code == 200:
                    data_1 = response_1.json()
                    data_2 = response_2.json()

                    # Extract holdings for both funds
                    holdings_1 = set(holding['securityName'] for holding in data_1.get('equityHoldingPage', {}).get('holdingList', []))
                    holdings_2 = set(holding['securityName'] for holding in data_2.get('equityHoldingPage', {}).get('holdingList', []))

                    # Calculate overlap
                    overlap = holdings_1.intersection(holdings_2)

                    # Display overlap results
                    st.write(f"### Overlap Between Funds `{fund_id_1}` and `{fund_id_2}`")
                    
                    # Create a DataFrame for common holdings
                    if overlap:
                        common_holdings_df = pd.DataFrame(list(overlap), columns=["Common Holdings"])
                        st.table(common_holdings_df)

                        st.write(f"**Number of Common Holdings:** {len(overlap)}") 
                        st.write(len(holdings_1))
                        a= (len(overlap) / ((len(holdings_1) + len(holdings_2)))) * 100
                        st.write(f" percentage of common Holdings: {a}")
                        # Create Venn Diagram
                        plt.figure(figsize=(8, 8))
                        venn2([holdings_1, holdings_2], ('Fund 1', 'Fund 2'))
                        plt.title('Fund Overlap Analysis', fontsize=16)
                        st.pyplot(plt)
                    else:
                        st.write("No common holdings found between the two funds.")
                else:
                    st.warning("Unable to fetch data for one or both Fund IDs.")
            else:
                st.warning("Please enter both Fund IDs to compare.")

def about():
        pass

st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Select a page:", ["Home", "Holdings", "About"])

# Render the selected page
if page == "Home":
    home()
elif page == "Holdings":
    Holdings()

elif page == "About":
    about()




















