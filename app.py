import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- 1. Dashboard Configuration ---
st.set_page_config(page_title="50-30-20 Expense Analyzer", layout="wide")
st.title("📊 AI Expense Dashboard: The 50-30-20 Rule")
st.write("Upload your bank statement and let the AI categorize your spending!")

# --- 2. Secure API Key Configuration ---
# This pulls YOUR hidden key from Streamlit Cloud so students don't need one
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Instructor Note: API Key not found in Streamlit Secrets.")

# --- 3. File Uploader ---
uploaded_file = st.file_uploader("Upload your bank statement (CSV format)", type=["csv"])

@st.cache_data
def categorize_expenses_with_ai(descriptions):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a financial advisor. I will give you a list of bank transaction descriptions. 
    Categorize each one strictly into ONE of these three categories based on the 50-30-20 rule:
    - 'Need' (groceries, rent, utilities, insurance, basic transport)
    - 'Want' (dining out, entertainment, shopping, hobbies)
    - 'Investment' (savings transfers, stock purchases, retirement funds, loan overpayments)
    
    Return ONLY a valid JSON object where the keys are the exact descriptions and the values are the categories.
    Descriptions: {descriptions}
    """
    
    response = model.generate_content(prompt)
    
    try:
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        st.error("There was an issue parsing the AI response. Please try again.")
        return {}

# --- 4. Main App Logic ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    if "Description" in df.columns and "Amount" in df.columns:
        st.success("File uploaded successfully!")
        
        with st.spinner("AI is analyzing your expenses..."):
            unique_desc = df['Description'].dropna().unique().tolist()
            category_mapping = categorize_expenses_with_ai(unique_desc)
            df['Category'] = df['Description'].map(category_mapping)
            
            # Ensure amounts are positive numbers and handle commas
            df['Amount'] = pd.to_numeric(df['Amount'].astype(str).str.replace(',', ''), errors='coerce').abs()
            
            summary = df.groupby('Category')['Amount'].sum().reset_index()
            total_spent = summary['Amount'].sum()
            summary['Percentage'] = (summary['Amount'] / total_spent) * 100
            
            # --- 5. Visualizing the Data ---
            st.subheader("Your 50-30-20 Breakdown")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                fig = px.pie(summary, values='Amount', names='Category', 
                             title="Expense Distribution",
                             color='Category',
                             color_discrete_map={'Need': '#ef553b', 'Want': '#636efa', 'Investment': '#00cc96'})
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.write("### Summary Table")
                st.dataframe(summary.style.format({'Amount': '${:,.2f}', 'Percentage': '{:.1f}%'}))
                
                st.write("### How are you doing?")
                needs_pct = summary[summary['Category'] == 'Need']['Percentage'].sum() if not summary[summary['Category'] == 'Need'].empty else 0
                if needs_pct > 50:
                    st.warning(f"Your Needs are at {needs_pct:.1f}%. Try to keep them under 50%.")
                else:
                    st.success(f"Great job! Your Needs are at {needs_pct:.1f}%, which is within the 50% target.")
    else:
        st.error("Please ensure your CSV file has columns named 'Description' and 'Amount'.")
