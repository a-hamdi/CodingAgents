import json
import os
import subprocess
import time
from datetime import datetime
from typing_extensions import TypedDict
import google.generativeai as genai

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

def execute_code(language, filepath):
    """Executes a code file written in the specified language."""
    print(f"Executing {language} code in file: {filepath}")

    command = {
        "python": ["python", filepath],
        "c": ["gcc", filepath, "-o", "./a.out"],
        "js": ["node", filepath]
    }.get(language)

    if language == "c":
        try:
            subprocess.run(command, check=True)
            command = ["./a.out"]
        except subprocess.CalledProcessError as e:
            return "", f"Compilation Error:\n{e.stderr.strip()}"

    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return "", e.stderr.strip()
    finally:
        if language == "c" and os.path.exists("./a.out"):
            os.remove("./a.out")

def parse_code(raw_code):
    """Parses and extracts valid code from raw response."""
    if raw_code.startswith("```") and raw_code.endswith("```"):
        return "\n".join(raw_code.splitlines()[1:-1])
    return raw_code.strip()

def get_timestamp():
    """Returns the current time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def host(prompt, language, samples, max_iterations=3, agents=None):
    """Manages the workflow: generates, validates, and refines code while testing samples."""
    
    conversation_log = []
    iteration = 1
    file_extension = {"python": "py", "c": "c", "js": "js", "nvcc": "cu"}.get(language, "txt")
    filename = f"task.{file_extension}"
    if len(agents)==4:
        # Initialize agents
        agent_1 = create_agent(agents[0], generation_config_normal)  
        agent_2 = create_agent(agents[1], generation_config_normal)  
        agent_3 = create_agent(agents[2], generation_config_structured)  
        agent_4 = create_agent(agents[3], generation_config_normal)  
        agent_5= create_agent(agents[4], generation_config_normal)  
    else:
        # Initialize agents
        agent_1 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal)  
        agent_2 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal)  
        agent_3 = create_agent("gemini-2.0-flash-exp", generation_config_structured)  
        agent_4 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal) 
        agent_5 = create_agent("gemini-2.0-flash-thinking-exp-01-21", generation_config_normal)  

    while iteration <= max_iterations or max_iterations == -1:
        print(f"\n=== Iteration {iteration}: Agent 1 generates/refines a code snippet ===")
        
        if iteration % 2 == 0:
            print("\n--- Sleeping for rate limiting ---")
            time.sleep(10)

        timestamp = get_timestamp()

        # Step 1: Agent 1 generates/refines the code 
        while True:
            try:
                conversation_log.append(f"""{get_timestamp()} | Iteration {iteration} |       host:
                    Write {language} code for the following task. Only return the code:\n{prompt}"""           
                                                        )
                agent_1_response = agent_1.send_message(conversation_log)
                
                raw_code = agent_1_response.text.strip()
                break
            except Exception as e:
                if '429' in str(e):
                    print("Rate limit exceeded when calling Agent 1. Retrying...")
                    time.sleep(30)
                    continue
                else:
                    print(f"Unexpected error when calling Agent 1: {e}")
                    return "no", "", "Error communicating with Agent 1."

        refined_code = parse_code(raw_code)

        print("Agent 1 Output (Refined Code):\n", refined_code)
        conversation_log.append(f"{timestamp} | Iteration {iteration} | Agent 1 -> Agent 2 :\n{refined_code}")

        # Step 2: Agent 2 validates the code
        print(f"\n=== Iteration {iteration}: Agent 2 validates the refined code ===")
        while True:
            try:
                conversation_log.append(f"""{get_timestamp()} | Iteration {iteration} |       host:
                    Validate if the following {language} code is error-free and handles the task properly.\n
                    Respond 'Yes' or 'No'.\n\n{refined_code}"""           
                                                        )
                agent_2_response = agent_2.send_message(conversation_log)
                conversation_log.append(f"{timestamp} | Iteration {iteration} | Agent 2 -> Agent 1:\n{agent_2_response.text.strip()}")

                
                break
            except Exception as e:
                if '429' in str(e):
                    print("Rate limit exceeded when calling Agent 2. Retrying...")
                    time.sleep(30)
                    continue
                else:
                    print(f"Unexpected error when calling Agent 2: {e}")
                    return "no", "", "Error communicating with Agent 2."

        validation_decision = agent_2_response.text.strip().lower()
        print("Agent 2 Decision:", validation_decision)

        if "yes" not in validation_decision:
            print("\n=== Code validation failed. Retry with Agent 1 ===")
            conversation_log.append(f"{get_timestamp()} | Iteration {iteration} | Validation failed. Retrying...")
            
            continue

        with open(filename, "w") as code_file:
            code_file.write(refined_code)
        print(f"\n=== Code saved to {filename} ===")
        conversation_log.append(f"{timestamp} | Iteration {iteration} |Agent 2 -> agent1: Validated code saved to file.")
        
        # Step 3: Agent 4 creates customized code for each sample
        print(f"\n=== Iteration {iteration}: Agent 4 modifies code for testing ===")

        sample_results = []
        for i, sample in enumerate(samples):
            sample_input = sample["input"]
            expected_output = sample["expected_output"]
            counter=3
            while True and counter>0:
                try:

                    conversation_log.append(f"""{get_timestamp()} | Iteration {iteration} |    host:
                        Modify the following Python code so it directly uses the sample input: {sample_input}.
Only write the modified code below. Avoid outputting explanations or additional comments.
Code:
{refined_code}"""           
                                                        )
                    agent_4_response = agent_4.send_message(conversation_log)

                    conversation_log.append(f"{timestamp} | Iteration {iteration} | Agent 4 -> Agent5:\n{agent_4_response.text.strip()}")
                    modified_code = parse_code(agent_4_response.text.strip())
                                        # Save the modified code to a sample-specific file
                    sample_filename = f"task_sample_{i + 1}.{file_extension}"
                    with open(sample_filename, "w") as sample_file:
                        sample_file.write(modified_code)

                    print(f"Modified Code for Sample {i + 1} saved to {sample_filename}")
                    # Step 4: Agent 5 validates the code
                    print(f"\n=== Iteration {iteration}: Agent 5 validates the refined sample code ===")
                    while True and counter>0:
                        try:
                            
                            conversation_log.append(f"""{get_timestamp()} | Iteration {iteration} | host:Validate the functionality of this adapted Python code. It should:
1. Pass sample input `{sample_input}` correctly.
2. Retain the task's functionality.
3. Be free of syntax issues. 
4. if it fails, provide a detailed suggestions
Modified code:
{modified_code}

"""              
                                    )
                            agent_5_response = agent_5.send_message(conversation_log)


                            validation_decision = agent_5_response.text.strip().lower()
                            print("Agent 5 Decision:", validation_decision)

                            if "yes" not in validation_decision:
                                print("\n=== Code validation failed. Retry with Agent 4 ===")
                                conversation_log.append(f"{get_timestamp()} | Iteration {iteration} | Agent 5 -> Agent 4  : Validation failed. {validation_decision}")
                                counter-=1
                                continue
                            break
                        
                        except Exception as e:
                            if '429' in str(e):
                                print("Rate limit exceeded when calling Agent 2. Retrying...")
                                time.sleep(30)  # Wait before retrying
                                continue  # Retry this iteration
                            else:
                                print(f"Unexpected error when calling Agent 2: {e}")
                                return "no", "", "Error communicating with Agent 2."

                        




                    terminal_output, terminal_error = execute_code(language, sample_filename)

                    sample_results.append({
                        "sample_index": i + 1,
                        "input": sample_input,
                        "expected_output": expected_output,
                        "actual_output": terminal_output.strip(),
                        "error": terminal_error.strip(),
                        "passed": terminal_output.strip() == expected_output
                    })
                    break

                except Exception as e:
                    print(f"Error processing sample {i + 1}: {e}")
                    sample_results.append({
                        "sample_index": i + 1,
                        "input": sample_input,
                        "expected_output": expected_output,
                        "actual_output": "",
                        "error": str(e),
                        "passed": False
                    })
                    time.sleep(30)
                    continue

        # Step 4: Agent 3 analyzes test results
        print("\n=== Iteration {}: Agent 3 analyzes test results ===".format(iteration))
        test_summary = {
            "sample_results": sample_results,
            "total_samples": len(samples),
            "passed_tests": sum(1 for result in sample_results if result["passed"]),
            "failed_tests": sum(1 for result in sample_results if not result["passed"]),
        }
        while True:
            try:
                conversation_log.append(f"""{get_timestamp()} | Iteration {iteration} | host -> agent 3:The following test results were obtained by executing code on the provided samples:
                    {json.dumps(test_summary, indent=2)}
                    Does the code achieve the desired task? Respond in JSON format with:\n
                    if no samples exist, check the code itself and respond accordingly\n"
                    'response': 'yes' or 'no', and 'explanation': A detailed explanation.") """                   
                )
                agent_3_response = agent_3.send_message(conversation_log)

                
                agent_3_output = json.loads(agent_3_response.text.strip())
                decision = agent_3_output.get("response", "no").lower()
                explanation = agent_3_output.get("explanation", "")
                break
                
                  
            except json.JSONDecodeError as e:
                print("Error decoding Agent 3 response:", e)
                print("Raw Agent 3 Response:", agent_3_response.text.strip())
                explanation = "Failed to parse Agent 3 response."

            except Exception as e:
                if '429' in str(e):
                    print("Rate limit exceeded when calling Agent 3. Retrying...")
                    time.sleep(30)
                    continue
                else:
                    print(f"Unexpected error when calling Agent 3: {e}")
                    return "no", "", "Error communicating with Agent 3."
        print("Agent 3 Decision:", decision)
        print("Agent 3 Explanation:", explanation)

        if "yes" in decision:
            print("\n=== Workflow Complete: Code works as expected ===")
            
            return "yes", refined_code, explanation
        conversation_log.append(f"{timestamp} | Iteration {iteration} | Agent 3 -> Host:\n{decision}, {explanation}")         
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
