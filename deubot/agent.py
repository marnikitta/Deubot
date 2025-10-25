from typing import Any, cast
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from deubot.database import PhrasesDB


SYSTEM_PROMPT = """You are a German language learning assistant. Your primary role is to help users learn German through translation and spaced repetition.

## Core Capabilities

### Translation Mode (Primary)
- When a user sends a message, determine if it's English or German
- Translate: English -> German or German -> English
- For new conversations or first messages, provide:
  - The translation
  - Contextual information about usage
  - Example sentences demonstrating typical usage
  - Grammar notes if relevant

### Conversation Management
- Analyze each message to determine if it's a new conversation or continuation
- Consider it a new conversation if:
  - The topic has significantly changed
  - The user is starting a completely different query
  - There's no clear connection to previous messages
- When you detect a new conversation, the message history will be cleared automatically

### Spaced Repetition Mode
- When user requests spaced repetition practice, enter review mode
- Present phrases in German that are due for review
- User will rate their recall with buttons (Again=1, Hard=2, Good=3, Easy=4)
- Guide the session, showing one phrase at a time
- Celebrate progress and provide encouragement

### Phrase Management
- When translating new words/phrases in translation mode, save interesting or useful items to the database
- Use your judgment to save phrases that would be valuable for learning
- Include contextual information when saving

## Tool Usage

You have access to these tools:
- save_phrase: Save a new German-English phrase pair with context
- get_all_phrases: Retrieve all saved phrases with statistics
- get_due_phrases: Get phrases that are due for review in spaced repetition
- update_review: Update a phrase's spaced repetition statistics after review

Use tools proactively to enhance the learning experience. Save valuable translations automatically, and manage spaced repetition sessions smoothly.

## Tone
- Be friendly, encouraging, and educational
- Explain grammar points clearly when relevant
- Provide cultural context for phrases when appropriate
- Make learning feel natural and conversational"""


class GermanLearningAgent:
    def __init__(self, api_key: str, model: str, db: PhrasesDB):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.db = db
        self.tools: list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": "save_phrase",
                    "description": "Save a new German-English phrase pair to the learning database. Use this when translating interesting or useful words/phrases that would be valuable for the user to remember.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "german": {"type": "string", "description": "The German word or phrase"},
                            "english": {"type": "string", "description": "The English translation"},
                            "context": {
                                "type": "string",
                                "description": "Additional context, example usage, or grammar notes",
                            },
                        },
                        "required": ["german", "english", "context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_phrases",
                    "description": "Get all saved phrases with their statistics (review count, ease factor, next review date)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_due_phrases",
                    "description": "Get phrases that are currently due for spaced repetition review",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_review",
                    "description": "Update a phrase's spaced repetition statistics after user reviews it. Quality: 1=Again (complete forget), 2=Hard (difficult to recall), 3=Good (recalled with effort), 4=Easy (recalled easily)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phrase_id": {"type": "string", "description": "The ID of the phrase being reviewed"},
                            "quality": {
                                "type": "integer",
                                "description": "Quality of recall: 1=Again, 2=Hard, 3=Good, 4=Easy",
                                "minimum": 1,
                                "maximum": 4,
                            },
                        },
                        "required": ["phrase_id", "quality"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "should_clear_history",
                    "description": "Determine if the current message represents a new conversation that should reset the message history. Returns true if history should be cleared.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "is_new_conversation": {
                                "type": "boolean",
                                "description": "True if this is a new conversation unrelated to previous messages",
                            }
                        },
                        "required": ["is_new_conversation"],
                    },
                },
            },
        ]

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name == "save_phrase":
            phrase_id = self.db.add_phrase(
                german=arguments["german"], english=arguments["english"], context=arguments["context"]
            )
            return f"Phrase saved successfully with ID: {phrase_id}"

        elif tool_name == "get_all_phrases":
            phrases = self.db.get_all_phrases()
            return f"Found {len(phrases)} phrases: {phrases}"

        elif tool_name == "get_due_phrases":
            phrases = self.db.get_due_phrases()
            return f"Found {len(phrases)} phrases due for review: {phrases}"

        elif tool_name == "update_review":
            self.db.update_review(phrase_id=arguments["phrase_id"], quality=arguments["quality"])
            return f"Review updated for phrase {arguments['phrase_id']} with quality {arguments['quality']}"

        elif tool_name == "should_clear_history":
            return f"History clear decision: {arguments['is_new_conversation']}"

        return "Unknown tool"

    def process_message(self, messages: list[dict[str, str]]) -> tuple[str, bool]:
        messages_with_system: list[ChatCompletionMessageParam] = [
            cast(ChatCompletionMessageParam, {"role": "system", "content": SYSTEM_PROMPT})
        ]
        messages_with_system.extend(cast(list[ChatCompletionMessageParam], messages))

        response = self.client.chat.completions.create(
            model=self.model, messages=messages_with_system, tools=self.tools, temperature=0.7
        )

        should_clear = False
        while response.choices[0].finish_reason == "tool_calls":
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls
            if not tool_calls:
                break

            messages_with_system.append(
                cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name if hasattr(tc, "function") else "",
                                    "arguments": tc.function.arguments if hasattr(tc, "function") else "",
                                },
                            }
                            for tc in tool_calls
                        ],
                    },
                )
            )

            for tool_call in tool_calls:
                import json

                if not hasattr(tool_call, "function"):
                    continue

                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "should_clear_history":
                    should_clear = tool_args.get("is_new_conversation", False)

                result = self._execute_tool(tool_name, tool_args)
                messages_with_system.append(
                    cast(ChatCompletionMessageParam, {"role": "tool", "tool_call_id": tool_call.id, "content": result})
                )

            response = self.client.chat.completions.create(
                model=self.model, messages=messages_with_system, tools=self.tools, temperature=0.7
            )

        return response.choices[0].message.content or "", should_clear
