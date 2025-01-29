from datetime import datetime
import subprocess
import json  # To help handle JSON responses
import json
import subprocess
from datetime import datetime
from typing_extensions import TypedDict
import google.generativeai as genai
import time
class Agent3Response(TypedDict):
    response: str  # "yes" or "no"
    explanation: str  # Detailed explanation

# Generation configurations
generation_config_normal = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
}
generation_config_structured = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "application/json",
    "response_schema": Agent3Response
}

def create_agent(model_name, config):
    """Creates a chat session using the specified model and configuration."""
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=config,
    )
    return model.start_chat(history=[])
# Helper function to get the current timestamp
def get_timestamp():
    """Returns the current time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_code(raw_code):
    """
    Parses the raw response and extracts valid code.
    Removes markdown code block markers (```). 
    """
    if raw_code.startswith("```") and raw_code.endswith("```"):
        lines = raw_code.splitlines()
        return "\n".join(lines[1:-1])  # Remove code block markers
    return raw_code  # Return as-is if no markers


def execute_code(language, filepath):
    """
    Executes the file based on the specified programming language.
    Runs the compiled or interpreted code and returns output and errors.
    """
    if language == "python":
        # Execute Python code file
        command = ["python", filepath]
    elif language == "c":
        # Compile and run C code
        binary = filepath.replace(".c", ".out")  # Replace extension for binary
        compile_command = ["gcc", filepath, "-o", binary]  # Compile
        subprocess.run(compile_command, text=True, capture_output=True, check=True)
        command = [f"./{binary}"]
    elif language == "js":
        # Run JavaScript code using Node.js
        command = ["node", filepath]
    elif language == "nvcc":
        # Compile CUDA code and run
        binary = filepath.replace(".cu", ".out")  # Replace extension for binary
        compile_command = ["nvcc", filepath, "-o", binary]  # Compile
        subprocess.run(compile_command, text=True, capture_output=True, check=True)
        command = [f"./{binary}"]
    else:
        raise ValueError(f"Unsupported language: {language}")

    # Run the command and collect output
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return result.stdout, result.stderr
def host(prompt, language, samples, max_iterations=3, agents=None):
    if len(agents) == 3:
        # Initialize agents
        agent_1 = create_agent(agents[0], generation_config_normal)
        agent_2 = create_agent(agents[1], generation_config_normal)
        agent_3 = create_agent(agents[2], generation_config_structured)
    else:
        # Initialize agents with default models
        agent_1 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal)
        agent_2 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal)
        agent_3 = create_agent("gemini-2.0-flash-exp", generation_config_structured)

    """Manages the workflow: generates, validates, and refines code."""
    conversation_log = []
    iteration = 1
    file_extension = {"python": "py", "c": "c", "js": "js", "nvcc": "cu"}.get(language, "txt")
    filename = f"task.{file_extension}"

    while iteration <= max_iterations or max_iterations == -1:
        print(f"\n=== Iteration {iteration}: Agent 1 generates/refines a code snippet ===")

        if iteration % 2 == 0:
            print("\n--- Sleeping for rate limiting ---")
            time.sleep(10)

        timestamp = get_timestamp()

        # Step 1: Agent 1 generates/refines the code
        while True:
            try:
                agent_1_response = agent_1.send_message(
                    f"Write {language} code for the following task. Only return the code:\n{prompt}"
                )
                raw_code = agent_1_response.text.strip()
                break
            except Exception as e:
                if '429' in str(e):  # Check for Too Many Requests directly in the error message
                    print("Rate limit exceeded when calling Agent 1. Retrying...")
                    time.sleep(30)  # Wait before retrying
                    continue  # Retry this iteration
                else:
                    print(f"Unexpected error when calling Agent 1: {e}")
                    return "no", "", "Error communicating with Agent 1."

        refined_code = parse_code(raw_code)
        print("Agent 1 Output (Refined Code):\n", refined_code)
        conversation_log.append(f"{timestamp} | Iteration {iteration} | Agent 1 -> Host:\n{refined_code}")

        # Step 2: Agent 2 validates the code
        print(f"\n=== Iteration {iteration}: Agent 2 validates the refined code ===")
        while True:
            try:
                agent_2_response = agent_2.send_message(
                    f"Validate if the following {language} code is error-free and handles the task properly.\n"
                    f"Respond 'Yes' or 'No'.\n\n{refined_code}"
                )
                break
            except Exception as e:
                if '429' in str(e):
                    print("Rate limit exceeded when calling Agent 2. Retrying...")
                    time.sleep(10)  # Wait before retrying
                    continue  # Retry this iteration
                else:
                    print(f"Unexpected error when calling Agent 2: {e}")
                    return "no", "", "Error communicating with Agent 2."

        validation_decision = agent_2_response.text.strip().lower()
        print("Agent 2 Decision:", validation_decision)

        if "yes" not in validation_decision:
            print("\n=== Code validation failed. Retry with Agent 1 ===")
            conversation_log.append(f"{get_timestamp()} | Iteration {iteration} | Validation failed. Retrying...")
            iteration += 1
            continue

        # Save the validated code
        with open(filename, "w") as code_file:
            code_file.write(refined_code)
        print(f"\n=== Code saved to {filename} ===")
        conversation_log.append(f"{timestamp} | Iteration {iteration} | Validated code saved to file.")

        # Step 3: Agent 3 analyzes test results and decision-making
        print("\n=== Iteration {iteration}: Agent 3 analyzes validation results ===")
        test_summary = {
            "validated_code": refined_code,
        }
        while True:
            try:
                agent_3_response = agent_3.send_message(
                    f"The following code has been validated:\n\n"
                    f"{json.dumps(test_summary, indent=2)}\n\n"
                    "Does the code achieve the desired task? Respond in JSON format with:\n"
                    "'response': 'yes' or 'no', and 'explanation': A detailed explanation."
                )

                agent_3_output = json.loads(agent_3_response.text.strip())
                decision = agent_3_output.get("response", "no").lower()
                explanation = agent_3_output.get("explanation", "")

                print("Agent 3 Decision:", decision)
                print("Agent 3 Explanation:", explanation)

                if "yes" in decision:
                    print("\n=== Workflow Complete: Code works as expected ===")
                    return "yes", refined_code, explanation
                break

            except json.JSONDecodeError as e:
                print("Error decoding Agent 3 response:", e)
                print("Raw Agent 3 Response:", agent_3_response.text.strip())
                explanation = "Failed to parse Agent 3 response."

            except Exception as e:
                if '429' in str(e):
                    print("Rate limit exceeded when calling Agent 3. Retrying...")
                    time.sleep(10)  # Wait before retrying
                    continue  # Retry this agent
                else:
                    print(f"Unexpected error when calling Agent 3: {e}")
                    return "no", "", "Error communicating with Agent 3.",

        # Retry with new refinement
        iteration += 1
        print("\n--- Refining Code ---")

    return "no", refined_code, "Maximum iterations reached without achieving success."


def main():
    config_file = 'config.json'

    # Load configuration from file
    with open(config_file, 'r') as file:
        config = json.load(file)

    # Set the API key
    genai.configure(api_key=config['apikey'])

    final_status, final_code, final_explanation = host(
        config['prompt'],
        language=config['language'],
        samples=config['samples'], 
        max_iterations=config['max_iterations'],
        agents=config['agents']
    )

    print("\n=== Final Status ===")
    print("Status:", final_status)
    print("Refined Code:\n", final_code)
    print("Explanation:", final_explanation)


if __name__ == "__main__":
    main()
