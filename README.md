# CodingAgents

## Project Overview
The **CodingAgents** is a Multi-Agent Code Generation and Validation System which leverages advanced generative AI models, specifically Google's Gemini, to automate the process of code generation, refinement, validation, and testing. This system exhibits a sophisticated workflow where multiple agents systematically interact to ensure the production of high-quality code that meets the specified requirements. The project effectively demonstrates the integration of Natural Language Processing (NLP) with automated code execution, significantly enhancing coding efficiency and reliability.

![logo](logo.png)

## Features
- **AI-Powered Code Generation:** Uses Google Gemini models to generate programming code based on prompts.
- **Automated Code Validation:** Analyzes and verifies the correctness of generated code using AI.
- **Code Execution and Testing:** Runs validated code against predefined test samples and captures output for analysis.
- **Structured Decision-Making:** Implements a structured JSON schema for analyzing terminal results, particularly with the third agent performing structured output analysis.
- **Multi-Iteration Workflow:** Refines code iteratively until validation is successful, allowing for continuous improvement.
- **Multi-Agent System:** Simultaneously employs multiple AI agents collaborating to enhance the quality of the code.
- **Broad Language Support:** Supports various programming languages including Python, C, JavaScript, and more.
- **Logging and Monitoring:** Maintains a comprehensive log of all interactions and system states for traceability and debugging.

## System Architecture
There are two systems:
### System 1 (stable)
- **Agent 1:** Generates or refines code based on user prompts.
- **Agent 2:** Validates the correctness and functionality of the generated code.
- **Agent 3:** Analyzes terminal output, utilizing structured output capability to provide a final decision on the correctness of the code.

### System 2 (alpha)

- **All System 1 agents**
- **Agent 4:** Modifies code for specific test samples to facilitate tailored testing.

### System 3(beta)
- **All System 2 agents**
- **Agent 5:** Validates code of Agent 4.
- **communication between all agents is saved and passed in each prompt**

### 2. User Interaction Layer
Facilitates communication between users and the generative model, enabling the input of task descriptions and retrieval of final results.

### 3. Execution Engine
Executes generated code in various programming languages (Python, C, JavaScript) using subprocesses, ensuring isolation and management of execution environments.

### 4. Logging and Monitoring
Maintains comprehensive records of all interactions and system states, aiding debugging and analysis.

## Installation
To set up the environment, install the required dependencies using:
```sh
pip install -r requirements.txt
```

## Usage
1. Fit the configuration provided in `config.json` to set up your specific parameters.
2. Execute the main script:
```sh
python alpha/script.py
```

## Workflow Description
1. **Initialization:** Configures the API key for Gemini models and sets up generation parameters.
2. **Code Generation:** Agent 1 generates code based on user input.
3. **Code Validation:** Agent 2 validates the generated code for correctness.
4. **Iteration & Refinement:** If validation fails, the system refines the code through additional iterations.
5. **Sample Testing:** Agent 4 modifies the code for individual test cases.
6. **Code Execution:** The modified code is executed in the appropriate language.
7. **Result Analysis:** Agent 3 analyzes test results and provides final validation using structured output.
8. **Final Decision:** The system provides a comprehensive report on the outcome.

## Example Scenario
Consider a user requesting a Python function to sort a list using a custom comparator:
1. Agent 1 generates the sorting function.
2. Agent 2 validates the function.
3. Agent 4 modifies it for various test cases and executes it.
4. Agent 3 analyzes the results and confirms functionality.
5. The system reports the final outcome with explanations.

## Error Handling
- Implements retry mechanisms to handle API rate limits.
- Provides detailed execution logs for debugging.

## Future Enhancements
- Extend support for additional programming languages.
- Enhance execution tracking and debugging insights.
- Improve AI-driven error correction mechanisms.

## License
This project is released under the MIT License.

---
