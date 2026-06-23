import streamlit as st,pandas as pd,os,re
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
from sqlalchemy import create_engine
from google.oauth2 import service_account #type:ignore
from googleapiclient.discovery import build
from warnings import filterwarnings
filterwarnings('ignore')
load_dotenv()


os.environ['GROQ_API_KEY']=st.secrets.get('groq',os.getenv('groq'))
spreadsheet_1=st.secrets['google_sheet']['sheet_id']
range_name_1=st.secrets['google_sheet']['sheet_range']

st.title('A Simple Pokemon SQL Agent')

st.empty()
st.write('Try out the AI Agent by writing a simple Prompt')
with st.expander('Example of Prompts:'):
    st.write('List all Pokémon that are purely \'Fire\' type.')
    st.write('Find the stats for Pikachu')
    st.write('What is Bulbasaur\'s HP and Speed?')
    st.write('Which Pokémon has the highest total stat value?')
    st.write('What is the average Attack stat for Dragon-type Pokémon?')

scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_creds():
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_info,scopes=scopes)
    return build('sheets', 'v4', credentials=creds)

@st.cache_data(ttl=600)
def load_data_from_sheets_api(spreadsheet_id,range_name):
    """Fetches data using the Google Sheets JSON API and converts to a DataFrame"""
    # Load credentials
    service = load_creds()
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id, 
            range=range_name
        ).execute()
        data_rows = result.get('values', [])
    except Exception as e:
        st.error(f"Google API Error: {e}")
        return pd.DataFrame()
    if not data_rows:
        st.error("No data found in the specified range.")
        return pd.DataFrame()
    df = pd.DataFrame(data_rows[1:], columns=data_rows[0])
    return df

@st.cache_resource
def init_database():
    """Initializes the database and creates the columns required."""
    df = load_data_from_sheets_api(
        spreadsheet_id=spreadsheet_1, 
        range_name=range_name_1
    )
    if df.empty:
        return None, None, None
    df.columns = (
        df.columns.str.strip()
        .str.replace(' ', '_')
        .str.replace(r'[^\w]', '', regex=True)
    )
    engine = create_engine("sqlite:///pokemon.db", pool_pre_ping=True)
    df.to_sql('pokemon_data', engine, index=False, if_exists='replace')
    db = SQLDatabase(engine)
    
    return db, df, engine


def extract_clean_sql(text: str) -> str:
    """Strips the query from the text"""
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    clean_text = text.replace("**SQL Query:**", "").strip()
    return clean_text

def get_lean_schema(df):
    """Gets the column details"""
    columns_info = [f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)]
    return f"Table: pokemon_data\nColumns: {', '.join(columns_info)}"

#System Prompt One
db,df,engine=init_database()
llm=ChatGroq(model='llama-3.3-70b-versatile',temperature=0)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert SQLite developer. Given a question, write a correct SQLite query for the table 'pokemon_data'.\n\nSchema:\n{schema}\n\nCRITICAL: Return ONLY the raw SQL code wrapped inside a markdown code block. Do not include any explanations, introductory text, or conversational filler and always name your columns according to the question."),
    ("human", "{question}")
])
sql_chain = (
    RunnablePassthrough.assign(schema=lambda _: get_lean_schema(df))
    | prompt_template
    | llm
)

# Correction Prompt
correction_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert SQLite developer. The previous SQL query you generated failed with an error. Fix the query based on the schema and error message provided. Return ONLY the raw SQL code inside a code block."),
    ("human", "Schema:\n{schema}\n\nFailed Query:\n{failed_query}\n\nError Message:\n{error_msg}")
])

correction_chain = correction_prompt | llm | StrOutputParser()


# The Session States and variable saves
if 'current_df' not in st.session_state:
    st.session_state.current_df=None
if "query_success" not in st.session_state:
    st.session_state.query_success = False
if "last_sql" not in st.session_state:
    st.session_state.last_sql = ""
success=False
query_submit=False

# The Execution Area
if not df.empty:
    with st.expander("Preview Google Sheet Data"):
        st.dataframe(df.head())
    user_query = st.text_input("Ask a question about your data:",placeholder='Get the count of pokemon available')
    submit=st.button('Submit')
    if user_query and user_query!=' ' and submit:
        query_submit=True
        sql_query=sql_chain.invoke({'question':user_query})
        response=extract_clean_sql(sql_query.content)
        attempts=0
        max_attempts=3
        latest_error='Unknown Error Occurred'
        query_df=pd.DataFrame()
        with st.expander('Generated Data From SQL Query:'):
            st.code(sql_query.content,language='sql')
        with st.expander('LLM Metadata'):
            st.dataframe(data=sql_query.response_metadata)
        while attempts < max_attempts and not success:
            attempts+=1
            try:
                with engine.connect() as conn:
                    query_df = pd.read_sql_query(response, conn)
                    success=True
            except Exception as e:
                latest_error = str(e)
                if attempts < max_attempts:
                    st.warning(f"Attempt {attempts} failed. LLM is correcting the query...")
                    try:
                        raw_correction = correction_chain.invoke({
                        "schema": db.get_table_info(),
                        "failed_query": response,
                        "error_msg": str(e)
                        })
                        response=extract_clean_sql(raw_correction)
                        st.caption(f"🔄 Corrected Query Attempt {attempts + 1}:")
                        st.code(response, language='sql')
                    except Exception as chain_err:
                        latest_error = f"Correction Chain Failed: {str(chain_err)}"
                        break
        st.session_state.query_success = success
        st.session_state.current_df = query_df
        st.session_state.last_sql = response
        st.session_state.final_error = latest_error

# The Response Area
if query_submit:
    if st.session_state.query_success:
        st.success("Result:")
        if st.session_state.current_df is not None and not st.session_state.current_df.empty:
            display_df = st.session_state.current_df.copy()
            display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Query returned no results.")
    else:
        raw_error = st.session_state.get('final_error', "No diagnostic details available.")
        substituted_output = raw_error.replace("Groq API Error:", "[Groq LLM Notice]")
        substituted_output = substituted_output.replace("sqlite3.OperationalError:", "[Database Syntax Error]")
        substituted_output = substituted_output.replace("ProgrammingError", "[Query Execution Error]")
        st.error("❌ The agent was unable to resolve the SQL query after multiple attempts.")
        with st.expander("View Diagnostic Error Log"):
            st.text_area("Substituted Error Output", value=substituted_output, height=150)