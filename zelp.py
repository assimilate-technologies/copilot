# zelp.py

import os
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
# from langchain_openai import ChatOpenAI
from operator import itemgetter

from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

from langchain.chains.openai_tools import create_extraction_chain_pydantic
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import List
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

# from langchain.globals import set_verbose, set_debug

# examples
examples = [
    {
        "input": "List all employees.",
        "query": "SELECT * FROM `tabEmployee`;"
    },
    {
        "input": "List all employees reporting to Manal Ghadge",
        "query": "SELECT * FROM tabEmployee WHERE reports_to IN(SELECT name FROM tabEmployee WHERE first_name = 'Manal' AND last_name = 'Ghadge')",
    },
    {
        "input": "Who is manager of Nikhil Kadam?",
        "query": "SELECT * FROM tabEmployee WHERE name IN(SELECT reports_to FROM tabEmployee WHERE first_name = 'Nikhil' AND last_name = 'Kadam')",
    },
]

# ------------

# set_debug(True)
# set_verbose(True)

question = input("Enter your question:")

# question = "What is designation of Priyanka Belekar?"

# print(question)

# question = question + ". Final result should not include salary or ctc column if employee != 'AT012'"

print(question)

os.environ["OPENAI_API_KEY"] = ""

db = SQLDatabase.from_uri("")

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# --
class Table(BaseModel):
    """Table in SQL database."""

    name: str = Field(description="Name of table in SQL database.")

system = f"""Return the names of the SQL tables that are relevant to the user question. \
The tables are:

Employee
User
Leave"""
category_chain = create_extraction_chain_pydantic(Table, llm, system_message=system)

print(category_chain.invoke({ "input": question }))

# --

def get_tables(categories: List[Table]) -> List[str]:
    tables = []
    for category in categories:
        if category.name == "User":
            tables.extend(
                [
                    "tabUser",
                    "tabUser Type"
                ]
            )
        elif category.name == "Leave":
            tables.extend(["tabLeave Allocation"])
        elif category.name == "Employee":
            tables.extend(["tabEmployee"])
        
    return tables


table_chain = category_chain | get_tables  # noqa
print(table_chain.invoke({ "input": question }))

# --

# Convert "question" key to the "input" key expected by current table_chain.
table_chain = {"input": itemgetter("question")} | table_chain

employee_id = "AT012"
additional_filter = "Result should not include salary or ctc column if employee != '" + employee_id + "'"

example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
query_prompt = FewShotPromptTemplate(
    examples=examples[:5],
    example_prompt=example_prompt,
    prefix="""
    You are a mariadb expert.
    Given an input question, create a syntactically correct mariadb query to run.
    """ +additional_filter+ """
    Unless otherwise specified, do not return more than {top_k} rows.
    \n\nHere is the relevant table info: {table_info}\n\n
    Below are a number of examples of questions and their corresponding SQL queries.
    """,
    suffix="User input: {input}\nSQL query: ",
    input_variables=["input", "top_k", "table_info"],
)

# Create the SQL query chain.
query_chain = create_sql_query_chain(llm, db, prompt=query_prompt)

# Set table_names_to_use using table_chain.
query_chain = RunnablePassthrough.assign(table_names_to_use=table_chain) | query_chain

print(query_chain.invoke({ "question": question }))

execute_query_chain = QuerySQLDataBaseTool(db=db)

print(execute_query_chain.invoke({ "query": query_chain.invoke({ "question": question }) }))

answer_prompt = PromptTemplate.from_template(
    """Given the following user question, corresponding SQL query, and SQL result, answer the user question.
    Currency is specified in DB column else use INR.
    If query do not return any result then reply "Sorry! I'm not aware about how to resolve your query or you do not have access to view this data.
    My cool human creators are working day and night to add more features to me."

Question: {question}
SQL Query: {query}
SQL Result: {result}
Answer: """
)

answer = answer_prompt | llm | StrOutputParser()
chain = (
    RunnablePassthrough.assign(query=query_chain).assign(
        result=itemgetter("query") | execute_query_chain
    )
    | answer
)

finalAnswer = chain.invoke({ "question": question })
print(finalAnswer)

# ------------------------------

# table_names = "\n".join(db.get_usable_table_names())
# table_names = "\n tabUser"

# system = f"""Return the names of ALL the SQL tables that MIGHT be relevant to the user question. \
# The tables are:

# {table_names}

# Remember to include ALL POTENTIALLY RELEVANT tables, even if you're not sure that they're needed."""

# print(system)

# table_chain = create_extraction_chain_pydantic(Table, llm, system_message=system)
# d = table_chain.invoke({"input": question})

# print(d)


# execute_query = QuerySQLDataBaseTool(db=db)
# write_query = create_sql_query_chain(llm, db)

# answer_prompt = PromptTemplate.from_template(
#     """Given the following user question, corresponding SQL query, and SQL result, answer the user question.

# Question: {question}
# SQL Query: {query}
# SQL Result: {result}
# Answer: """
# )

# answer = answer_prompt | llm | StrOutputParser()
# chain = (
#     RunnablePassthrough.assign(query=write_query).assign(
#         result=itemgetter("query") | execute_query
#     )
#     | answer
# )

# finalAnswer = chain.invoke({ "question": question })
# print(finalAnswer)
