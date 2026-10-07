from ollama import chat
from datetime import datetime
import json
import re

# -----------------------------
# Calculator function
# -----------------------------

def calculator(a, b, operation):

    try:
        a = float(a)
        b = float(b)

        if operation == "add":
            return a + b

        elif operation == "subtract":
            return a - b

        elif operation == "multiply":
            return a * b

        elif operation == "divide":

            if b == 0:
                return "Cannot divide by zero"

            return a / b

        else:
            return "Unknown operation"

    except (ValueError, TypeError):
        return "Invalid numbers. Please provide valid numbers."


# -----------------------------
# Time function
# -----------------------------


def get_time():
    return datetime.now().strftime("%H:%M:%S")


def web_search(query):

    try:
        from ddgs import DDGS

        results = []

        with DDGS() as ddgs:

            search_results = ddgs.text(
                query,
                max_results=5
            )

            for result in search_results:

                results.append(
                    f"Title: {result['title']}\n"
                    f"URL: {result['href']}\n"
                    f"Description: {result['body']}"
                )

        if not results:
            return "No search results found."

        return "\n\n".join(results)

    except Exception as e:

        return f"Web search failed: {e}"

def save_memory(key, value):

    with open("memory.json", "r") as file:
        memories = json.load(file)

    # Check if the memory already exists
    for memory in memories:

        if memory["key"].lower() == key.lower():

            memory["value"] = value

            with open("memory.json", "w") as file:
                json.dump(memories, file, indent=4)

            return "Memory updated."

    # If memory does not exist, create a new one
    memories.append({
        "key": key,
        "value": value
    })

    with open("memory.json", "w") as file:
        json.dump(memories, file, indent=4)

    return "Memory saved."


def load_memory():
    with open("memory.json", "r") as file:
        return json.load(file)

def find_memory(key):
    memories = load_memory()

    for memory in memories:
        if memory["key"].lower() == key.lower():
            return memory["value"]

    return None

def get_all_memories():
    return load_memory()

# -----------------------------
# Basic Memory Retrieval
# -----------------------------

def retrieve_memory(question):

    memories = get_all_memories()

    question_lower = question.lower()

    for memory in memories:

        key = memory["key"].lower()

        if key in question_lower:
            return memory["value"]

    return None

# -----------------------------
# Decide which tools are needed
# -----------------------------

def choose_tools(question):

    question_lower = question.lower()

    if (
        "time" in question_lower
        or "current time" in question_lower
    ):
        return [tools[1]]

    elif (
        "+" in question
        or "-" in question
        or "*" in question
        or "/" in question
        or "add" in question_lower
        or "subtract" in question_lower
        or "multiply" in question_lower
        or "divide" in question_lower
        or "calculate" in question_lower
        or "sum" in question_lower
    ):
        return [tools[0]]

    elif (
        "search" in question_lower
        or "latest" in question_lower
        or "news" in question_lower
        or "today" in question_lower
        or "current" in question_lower
        or "recent" in question_lower
        or "newest" in question_lower
        or "who is" in question_lower
        or "what happened" in question_lower
    ):
        return [tools[2]]

    else:
        return []

# -----------------------------
# Agent Planning
# -----------------------------

def create_plan(task, retrieved_memory=None):

    task_lower = task.lower()

    # Multiple-tool task
    if (
        "time" in task_lower
        and (
            "+" in task
            or "-" in task
            or "*" in task
            or "/" in task
            or "calculate" in task_lower
        )
    ):
        return [
            "Identify the numbers and operation",
            "Perform the calculation",
            "Get the current time",
            "Give the results"
        ]

    if retrieved_memory:
        return [
            "Use the retrieved memory",
            "Give the answer using the remembered information"
        ]

    if "latest" in task_lower or "news" in task_lower:
        return [
            "Search the internet for current information",
            "Read the search results",
            "Summarize the important information"
        ]

    elif (
        "+" in task
        or "-" in task
        or "*" in task
        or "/" in task
        or "calculate" in task_lower
    ):
        return [
            "Identify the numbers and operation",
            "Perform the calculation",
            "Give the result"
        ]

    elif "time" in task_lower:
        return [
            "Get the current time",
            "Give the time to the user"
        ]

    else:
        return [
            "Understand the user's request",
            "Generate an appropriate answer"
        ]

# -----------------------------
# Execute Agent Plan
# -----------------------------

def execute_plan(plan, question):

    results = []

    for step_number, step in enumerate(plan, start=1):

        print(f"\nExecuting step {step_number}: {step}")

        if "Search the internet" in step:
            result = web_search(question)
            results.append(result)

        elif "Read the search results" in step:
            if results:
                print("Search results received.")
            else:
                print("No search results available.")

        elif "Summarize" in step:
            print("Preparing final answer...")


        elif "identify the numbers" in step.lower():

            print("Identifying the numbers and operation.")


        elif "calculation" in step.lower():

            print("Performing the calculation.")


        elif "give the result" in step.lower():

            print("Preparing the calculation result.")

        elif "current time" in step.lower():
            print("Time step identified.")

        else:
            print("Step understood.")

    return results

# -----------------------------
# Connect Plan to Tool
# -----------------------------

def get_tool_for_plan(plan):

    for step in plan:

        step_lower = step.lower()

        if "search the internet" in step_lower:
            return tools[2]       # web_search

        elif "calculation" in step_lower:
            return tools[0]       # calculator

        elif "current time" in step_lower:
            return tools[1]       # get_time

    return None

# -----------------------------
# Get Multiple Tools for Plan
# -----------------------------

def get_tools_for_plan(plan):

    selected_tools = []

    for step in plan:

        step_lower = step.lower()

        if "search the internet" in step_lower:
            selected_tools.append(tools[2])

        elif "calculation" in step_lower:
            selected_tools.append(tools[0])

        elif "current time" in step_lower:
            selected_tools.append(tools[1])

    return selected_tools

# -----------------------------
# Execute Selected Tool
# -----------------------------

def execute_tool(tool_name, arguments):

    try:

        if tool_name == "calculator":

            a = arguments["a"]
            b = arguments["b"]
            operation = arguments["operation"]

            return calculator(a, b, operation)

        elif tool_name == "get_time":

            return get_time()

        elif tool_name == "web_search":

            query = arguments["query"]

            return web_search(query)

        else:

            return "Unknown tool"

    except KeyError as e:

        return f"Missing tool argument: {e.args[0]}"

    except (TypeError, ValueError):

        return "Invalid tool arguments"

    except Exception as e:

        return f"Tool execution failed: {e}"


# -----------------------------
# Execute Multiple Tools
# -----------------------------

def execute_tools(tool_list, question):

    results = []

    for tool in tool_list:

        tool_name = tool["function"]["name"]

        print(f"\nExecuting tool: {tool_name}")

        if tool_name == "web_search":

            result = execute_tool(
                "web_search",
                {"query": question}
            )

            results.append(result)

        elif tool_name == "get_time":

            result = execute_tool(
                "get_time",
                {}
            )

            results.append(result)


        elif tool_name == "calculator":

            numbers = re.findall(r"\d+(?:\.\d+)?", question)

            if len(numbers) >= 2:

                a = float(numbers[0])

                b = float(numbers[1])

                if "*" in question or "multiply" in question.lower():

                    operation = "multiply"


                elif "+" in question or "add" in question.lower():

                    operation = "add"


                elif "-" in question or "subtract" in question.lower():

                    operation = "subtract"


                elif "/" in question or "divide" in question.lower():

                    operation = "divide"


                else:

                    operation = None

                if operation:

                    result = execute_tool(

                        "calculator",

                        {

                            "a": a,

                            "b": b,

                            "operation": operation

                        }

                    )

                    results.append(result)


                else:

                    print("Could not identify the calculation operation.")


            else:

                print("Could not identify the numbers.")

        else:

            print("Unknown tool:", tool_name)

    return results

#-----------------
# Check Task
#-----------------

def check_task_completion(tool_results):

    if not tool_results:
        return False

    for result in tool_results:

        if result is None:
            return False

        if isinstance(result, str):

            error_messages = [
                "Cannot divide by zero",
                "Invalid numbers",
                "Unknown tool",
                "Web search failed",
                "Missing tool argument",
                "Invalid tool arguments",
                "Tool execution failed"
            ]

            for error in error_messages:

                if error.lower() in result.lower():
                    return False

    return True

#------------------
#retry_task
#------------------


def retry_task(tool_name, arguments):

    print("Retrying task...")

    try:

        result = execute_tool(
            tool_name,
            arguments
        )

        return result

    except Exception as e:

        return f"Retry failed: {e}"

#----------------
#analyze_failure
#----------------

def analyze_failure(result):

    if not result:
        return "No result was returned."

    result_text = str(result).lower()

    if "cannot divide by zero" in result_text:
        return "The calculation failed because division by zero is not allowed."

    if "invalid numbers" in result_text:
        return "The calculation failed because the provided numbers are invalid."

    if "web search failed" in result_text:
        return "The web search failed, possibly because of an internet or search-service problem."

    if "unknown tool" in result_text:
        return "The requested tool does not exist."

    if "missing tool argument" in result_text:
        return "The tool did not receive all required arguments."

    if "invalid tool arguments" in result_text:
        return "The tool received invalid arguments."

    if "tool execution failed" in result_text:
        return "The tool encountered an execution error."

    return "The task failed for an unknown reason."

# -----------------------------
# Autonomous Task Execution
# -----------------------------

def run_autonomous_task(tool_name, arguments):

    print(f"Executing autonomous task with: {tool_name}")

    # First attempt
    result = execute_tool(
        tool_name,
        arguments
    )

    print("First attempt result:", result)

    # Check first attempt
    if check_task_completion([result]):

        print("Task completed successfully.")

        return result

    # First attempt failed
    print("Task failed.")

    # Retry
    retry_result = retry_task(
        tool_name,
        arguments
    )

    print("Retry result:", retry_result)

    # Check retry
    if check_task_completion([retry_result]):

        print("Retry successful.")

        return retry_result

    # Retry failed
    failure_reason = analyze_failure(retry_result)

    print("Failure analysis:", failure_reason)

    return failure_reason


# -----------------------------
# Tools
# -----------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Performs addition, subtraction, multiplication, or division.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform: add, subtract, multiply, or divide"
                    }
                },
                "required": ["a", "b", "operation"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Returns the current time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the internet and returns relevant web search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to use on the internet"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# -----------------------------
# Conversation memory
# -----------------------------
saved_memories = load_memory()

messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful AI agent. "
            f"Here is information remembered from previous conversations: {saved_memories} "
            "Use this information when it is relevant. "
            "Answer normal questions directly. "
            "If a tool is provided, use the tool through the tool-calling mechanism. "
            "Never write tool calls or JSON as your answer. "
            "For web search results, use the information returned by the tool "
            "to give the user a clear and direct answer. "
            "Always include the source title and URL for relevant web search results. "
            "Do not remove or hide URLs from search results."
        )
    }
]


# -----------------------------
# Main loop
# -----------------------------

if __name__ == "__main__":

    while True:

        question = input("You: ").strip()

        # -----------------------------
        # Handle empty input
        # -----------------------------

        if not question:
            print("AI: Please enter a question.")
            continue

        if question.lower() in ["exit", "quit"]:
            print("Agent stopped.")
            break

        retrieved_memory = retrieve_memory(question)


        if retrieved_memory:
            print("Memory retrieved:", retrieved_memory)
        else:
            print("No specific memory found.")

        saved_memories = get_all_memories()

        messages.append({
            "role": "user",
            "content": (
                f"Saved memories: {saved_memories}\n\n"
                f"User question: {question}"
            )
        })

        # -----------------------------
        # Create a plan
        # -----------------------------


        plan = create_plan(question, retrieved_memory)

        print("Plan:")

        for step_number, step in enumerate(plan, start=1):
            print(f"{step_number}. {step}")

        plan_results = execute_plan(plan, question)

        selected_tool = get_tool_for_plan(plan)

        if selected_tool:
            print("Tool selected from plan:", selected_tool["function"]["name"])
        else:
            print("No tool required.")

        # -----------------------------
        # Decide which tool is needed
        # -----------------------------

        question_lower = question.lower()

        # -----------------------------
        # Load current saved memories
        # -----------------------------

        saved_memories = get_all_memories()

        # -----------------------------
        # Handle memory commands
        # -----------------------------

        if question_lower.startswith("remember "):

            memory_text = question[9:].strip()

            if memory_text.lower().startswith("that "):
                memory_text = memory_text[5:]

            if " is " in memory_text.lower():

                key, value = memory_text.split(" is ", 1)

                key = key.strip()
                value = value.strip()

                save_memory(key, value)

                print("AI:", f"I will remember that {key} is {value}.")

            else:
                print("AI: Please use the format: remember X is Y.")

            continue


        # -----------------------------
        # Decide which tool is needed
        # -----------------------------

        available_tools = get_tools_for_plan(plan)

        print(
            "Tools selected:",
            [tool["function"]["name"] for tool in available_tools]
        )

        # -----------------------------
        # Execute multiple selected tools
        # -----------------------------

        if len(available_tools) > 1:

            tool_results = execute_tools(
                available_tools,
                question
            )

            print("\nTool results:")

            for result in tool_results:
                print(result)

            task_completed = check_task_completion(tool_results)

            if task_completed:
                print("Task completed successfully.")
            else:
                print("Task could not be completed.")

            # Give all tool results to the AI
            messages.append({
                "role": "user",
                "content": (
                    f"User request: {question}\n\n"
                    f"Tool results: {tool_results}\n\n"
                    "Use all the tool results to give one clear final answer."
                )
            })

            final_response = chat(
                model="llama3.2",
                messages=messages
            )

            print("AI:", final_response.message.content)

            messages.append(final_response.message)

            continue

        # Handle time directly

        if tools[1] in available_tools:

            task_failed = False

            time_result = run_autonomous_task(
                "get_time",
                {}
            )

            print("Time result:", time_result)

            if isinstance(time_result, str) and (
                    "failed" in time_result.lower()
                    or "error" in time_result.lower()
            ):

                print("AI:", time_result)

                messages.append({
                    "role": "assistant",
                    "content": time_result
                })

                task_failed = True

            else:

                final_answer = f"The current time is {time_result}."

                print("AI:", final_answer)

                messages.append({
                    "role": "assistant",
                    "content": final_answer
                })

            if task_failed:
                continue

            continue

        # Handle web search

        if tools[2] in available_tools:

            task_failed = False

            search_result = run_autonomous_task(
                "web_search",
                {
                    "query": question
                }
            )

            # Check if autonomous execution returned a failure
            if isinstance(search_result, str) and search_result.startswith(
                    "The web search failed"
            ):

                print("AI:", search_result)

                messages.append({
                    "role": "assistant",
                    "content": search_result
                })

                task_failed = True

            else:

                print("Web search completed.")

                messages.append({
                    "role": "tool",
                    "content": str(search_result)
                })

            if task_failed:
                continue

            final_response = chat(
                model="llama3.2",
                messages=messages
            )

            print("AI:", final_response.message.content)

            messages.append(final_response.message)

            continue


        # -----------------------------
        # Ask Llama
        # -----------------------------

        response = chat(
            model="llama3.2",
            messages=messages,
            tools=available_tools
        )


        # -----------------------------
        # Check if a tool was requested
        # -----------------------------

        if response.message.tool_calls:

            messages.append(response.message)

            task_failed = False
            direct_answer_given = False

            for call in response.message.tool_calls:

                # -----------------------------
                # Calculator tool
                # -----------------------------

                if call.function.name == "calculator":

                    a = call.function.arguments["a"]
                    b = call.function.arguments["b"]
                    operation = call.function.arguments["operation"]

                    result = run_autonomous_task(
                        "calculator",
                        {
                            "a": a,
                            "b": b,
                            "operation": operation
                        }
                    )

                    # Check if calculation failed
                    if isinstance(result, str) and (
                            "calculation failed" in result.lower()
                            or "failed" in result.lower()
                    ):

                        print("AI:", result)

                        messages.append({
                            "role": "assistant",
                            "content": result
                        })

                    else:

                        # Create the final answer directly
                        if operation == "add":
                            symbol = "+"
                        elif operation == "subtract":
                            symbol = "-"
                        elif operation == "multiply":
                            symbol = "*"
                        elif operation == "divide":
                            symbol = "/"
                        else:
                            symbol = operation

                        final_answer = f"The result of {a} {symbol} {b} is {result}."

                        print("AI:", final_answer)

                        messages.append({
                            "role": "assistant",
                            "content": final_answer
                        })
                        direct_answer_given = True

                    continue


                # -----------------------------
                # Time tool
                # -----------------------------
                # -----------------------------

                elif call.function.name == "get_time":

                    result = get_time()

                    print("Time result:", result)

                    messages.append({

                        "role": "tool",

                        "content": f"The current time is {result}"

                    })



                elif call.function.name == "web_search":

                    query = call.function.arguments["query"]

                    result = run_autonomous_task(

                        "web_search",

                        {

                            "query": query

                        }

                    )

                    # Check if autonomous execution returned a failure

                    if isinstance(result, str) and result.startswith("The web search failed"):

                        print("AI:", result)

                        messages.append({

                            "role": "assistant",

                            "content": result

                        })

                        task_failed = True


                    else:

                        print("Web search completed.")

                        messages.append({

                            "role": "tool",

                            "content": str(result)

                        })

            # -----------------------------
            # Stop after failed task
            # -----------------------------

            if task_failed:
                continue

            if direct_answer_given:
                continue


            # -----------------------------
            # Ask AI for final answer
            # -----------------------------

            final_response = chat(
                model="llama3.2",
                messages=messages
            )

            print("AI:", final_response.message.content)

            messages.append(final_response.message)


        else:

            print("AI:", response.message.content)

            messages.append(response.message)
