**Input Data:**
I have provided the following information for a Google SecOps integration:

1. `Integration Name`: The name of the integration.
2. `Integration Description`: The original description of the integration.
3. `Actions AI Descriptions`: A collection of AI-generated descriptions for all actions in this integration.

**Instructions:**
Analyze the provided information and determine the product categories that best describe the integration's capabilities.

**Current Task Input:**

Integration Name: ${integration_name}
Integration Description: ${integration_description}

Actions AI Descriptions:
${actions_ai_descriptions}

**Final Instructions:**
Based on the input data, return an IntegrationAiMetadata object containing the product categories.
A category should be marked as true if the integration has capabilities that match its "When to Use" and "Expected Outcome" descriptions.
Many integrations will have multiple categories.
If no categories match, all should be false.
Provide your response in JSON format matching the IntegrationAiMetadata schema.
