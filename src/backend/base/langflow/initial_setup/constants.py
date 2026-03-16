STARTER_FOLDER_NAME = "Starter Projects"
STARTER_FOLDER_DESCRIPTION = "Starter projects to help you get started in Langflow."

ASSISTANT_FOLDER_NAME = "Langflow Assistant"
ASSISTANT_FOLDER_DESCRIPTION = "Pre-built flows from Langflow Assistant to enhance your workflow."

# Legacy type aliases: maps old flow node type names to current component keys.
# SYNC: Keep in sync with api/utils/flow_validation.py and frontend reactflowUtils.ts
LEGACY_TYPE_ALIASES: dict[str, str] = {
    "Prompt": "Prompt Template",
}
