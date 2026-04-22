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
    # Read the file
    df = pd.read_csv(uploaded_file)
    
    # Clean up empty rows that banks sometimes leave at the top/bottom
    df.dropna(how='all', inplace=True)
    
    st.success("File uploaded successfully!")
    st.info("💡 Since every bank uses different labels, please tell the app which columns to read:")
    
    # Create dropdown menus for the user to map their columns
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        desc_col = st.selectbox("Which column has the Transaction Names/Narration?", df.columns)
    with col_sel2:
        amount_col = st.selectbox("Which column has the Expense Amount/Debit?", df.columns)
        
    # Add a button so the AI only runs when the user is ready
    if st.button("🚀 Analyze My Expenses"):
        with st.spinner("AI is categorizing your expenses. This takes a few seconds..."):
            
            # Get unique descriptions from the column the user chose
            unique_desc = df[desc_col].dropna().unique().tolist()
            category_mapping = categorize_expenses_with_ai(unique_desc)
            
            # Map the categories back to the dataframe
            df['Category'] = df[desc_col].map(category_mapping)
            
            # Clean up the amount column (removes commas and converts to numbers)
            df['Clean_Amount'] = pd.to_numeric(df[amount_col].astype(str).str.replace(',', ''), errors='coerce').abs()
            
            # Drop rows where the amount isn't a number (like blank lines)
            df = df.dropna(subset=['Clean_Amount'])
            
            # Calculate totals
            summary = df.groupby('Category')['Clean_Amount'].sum().reset_index()
            total_spent = summary['Clean_Amount'].sum()
            summary['Percentage'] = (summary['Clean_Amount'] / total_spent) * 100
            
            # --- 5. Visualizing the Data ---
            st.subheader("Your 50-30-20 Breakdown")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                fig = px.pie(summary, values='Clean_Amount', names='Category', 
                             title="Expense Distribution",
                             color='Category',
                             color_discrete_map={'Need': '#ef553b', 'Want': '#636efa', 'Investment': '#00cc96'})
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.write("### Summary Table")
                # Format the table for display
                display_summary = summary.copy()
                display_summary.columns = ['Category', 'Amount Spent', '% of Total']
                st.dataframe(display_summary.style.format({'Amount Spent': '₹{:,.2f}', '% of Total': '{:.1f}%'}))
                
                st.write("### How are you doing?")
                needs_pct = summary[summary['Category'] == 'Need']['Percentage'].sum() if not summary[summary['Category'] == 'Need'].empty else 0
                if needs_pct > 50:
                    st.warning(f"Your Needs are at {needs_pct:.1f}%. Try to keep them under the 50% target.")
                else:
                    st.success(f"Great job! Your Needs are at {needs_pct:.1f}%, which is within the 50% target.")
