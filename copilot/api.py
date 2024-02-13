import frappe
import os
import json
from typing import List
from operator import itemgetter
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.chains.openai_tools import create_extraction_chain_pydantic
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.globals import set_verbose, set_debug

@frappe.whitelist()
def get_chatbot_response(session_id: str, prompt_message: str) -> str:

	print(frappe.session.user)

	user_id = frappe.session.user
	
	employee_id = frappe.db.get_value("Employee", { "user_id": user_id }, "name")

	print(employee_id)

	question = prompt_message

	openai_model = get_model_from_settings()
	openai_api_key = get_key_from_settings()
	db_connection_string = get_db_connection_string_from_settings()
	examples = json.loads(get_examples_from_settings())

	print(db_connection_string)
	print(examples)

	categoriesTablesJSON = get_categories_tables_json_from_settings()
	categoriesTablesData = json.loads(categoriesTablesJSON)

	print(categoriesTablesJSON)
	print(categoriesTablesData)
	print(categoriesTablesData[0])

	if not openai_api_key:
		frappe.throw("Please set `OpenAI API Key` in settings")

	if not db_connection_string:
		frappe.throw("Please set `DB Connection String` in settings")

	set_debug(True)
	set_verbose(True)

	db = SQLDatabase.from_uri(db_connection_string)

	llm = ChatOpenAI(model=openai_model, temperature=0, openai_api_key=openai_api_key)

	class Table(BaseModel):
		"""Table in SQL database."""

		name: str = Field(description="Name of table in SQL database.")

	categories = '\n'.join([category['category'] for category in categoriesTablesData])
	print(categories)

	categoriesTablesMap = {}
	for category in categoriesTablesData:
		categoriesTablesMap[category['category']] = category['tables']

	print(categoriesTablesMap)

	system = f"""Return the names of the SQL tables that are relevant to the user question. \
	The tables are:

	{categories}"""

	print(system)

	category_chain = create_extraction_chain_pydantic(Table, llm, system_message=system)

	def get_tables(categories: List[Table]) -> List[str]:
		tables = []
		for category in categories:
			tablesToAdd = categoriesTablesMap[category.name]
			tables.extend(tablesToAdd)			
		return tables

	table_chain = category_chain | get_tables  # noqa
	table_chain = {"input": itemgetter("question")} | table_chain

	additional_filter = ""
	if employee_id:
		additional_filter = "If user is asking for salary or ctc column then only apply filter employee == '" + employee_id + "'"
	else:
		additional_filter = ""
	
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

	execute_query_chain = QuerySQLDataBaseTool(db=db)

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

	return finalAnswer


	# llm = OpenAI(model_name=openai_model, temperature=0, openai_api_key=openai_api_key)
	# message_history = RedisChatMessageHistory(
	# 	session_id=session_id,
	# 	url=frappe.conf.get("redis_cache") or "redis://localhost:6379/0",
	# )
	# memory = ConversationBufferMemory(memory_key="history", chat_memory=message_history)
	# conversation_chain = ConversationChain(llm=llm, memory=memory, prompt=prompt_template)

	# response = conversation_chain.run(prompt_message)
	# return response

def get_model_from_settings():
	return (
		frappe.db.get_single_value("Copilot Settings", "openai_model") or "gpt-3.5-turbo"
	)

def get_key_from_settings():
	return (
		frappe.db.get_single_value("Copilot Settings", "openai_api_key") or ""
	)

def get_db_connection_string_from_settings():
	return (
		frappe.db.get_single_value("Copilot Settings", "db_connection_string") or ""
	)

def get_categories_tables_json_from_settings():
	return (
		frappe.db.get_single_value("Copilot Settings", "categories_tables_json") or ""
	)

def get_examples_from_settings():
	return (
		frappe.db.get_single_value("Copilot Settings", "examples") or ""
	)
