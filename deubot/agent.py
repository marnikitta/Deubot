import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from openai import OpenAI

from deubot.database import PhrasesDB


@dataclass
class MessageOutput:
    message: str


@dataclass
class ShowReviewOutput:
    phrase_id: str
    german: str
    explanation: str


@dataclass
class LogOutput:
    message: str


@dataclass
class TypingOutput:
    pass


UserOutput = MessageOutput | ShowReviewOutput | LogOutput | TypingOutput


@dataclass
class ToolCallResult:
    result: str
    terminal: bool
    user_outputs: list[UserOutput]


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text()


class GermanLearningAgent:
    def __init__(self, api_key: str, model: str, db: PhrasesDB, enable_logs: bool = True):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.db = db
        self.enable_logs = enable_logs
        self.system_prompt = _load_system_prompt()
        self.messages: list[dict[str, str]] = []
        self.tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "name": "save_phrase",
                "description": "Save a new German phrase to the learning database.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "german": {"type": "string", "description": "The German word or phrase to be saved."}
                    },
                    "required": ["german"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_next_due_phrases",
                "description": "Get the next batch of German phrases that need review, returning a list of German phrases as strings (default: 30, max: 100).",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of phrases to return (default: 30, max: 100)",
                        }
                    },
                    "required": ["limit"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "show_review",
                "description": "Display a review card to the user with the German phrase, reveal button, and rating buttons, including an English explanation with translation, context, examples, and grammar notes.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phrase_id": {"type": "string", "description": "The ID of the phrase being reviewed"},
                        "german": {"type": "string", "description": "The German phrase to show"},
                        "explanation": {
                            "type": "string",
                            "description": "Full English explanation with translation, context, usage examples, and grammar notes",
                        },
                    },
                    "required": ["phrase_id", "german", "explanation"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_vocabulary",
                "description": "Get user's vocabulary with custom limit and sorting. Useful for creating sentences, estimating language level, or analyzing vocabulary knowledge.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of phrases to return (default: 100, max: 2000)",
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["alphabetical", "mastery", "id"],
                            "description": "Sort order: 'alphabetical' (A-Z), 'mastery' (by mastery level), 'id' (by addition order)",
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "Sort in ascending order if true, descending if false (default: true)",
                        },
                    },
                    "required": ["limit", "sort_by", "ascending"],
                    "additionalProperties": False,
                },
            },
        ]

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        if tool_name == "save_phrase":
            german = arguments["german"]
            phrase_id = self.db.add_phrase(german=german)
            return ToolCallResult(
                result=f"Phrase saved successfully with ID: {phrase_id}",
                terminal=False,
                user_outputs=[MessageOutput(message=f"✓ Saved: <b>{german}</b>")],
            )

        elif tool_name == "get_next_due_phrases":
            limit = min(arguments.get("limit", 30), 100)
            phrases = self.db.get_due_phrases(limit=limit)
            if phrases:
                german_phrases = [p["german"] for p in phrases]
                phrases_list = "\n".join([f"- {german}" for german in german_phrases])
                result = f"Found {len(phrases)} phrase(s) due for review:\n{phrases_list}"
            else:
                result = "No phrases due for review"
            return ToolCallResult(result=result, terminal=False, user_outputs=[])

        elif tool_name == "show_review":
            return ToolCallResult(
                result="Review shown to user. Waiting for user rating.",
                terminal=True,
                user_outputs=[
                    ShowReviewOutput(
                        phrase_id=arguments["phrase_id"],
                        german=arguments["german"],
                        explanation=arguments["explanation"],
                    )
                ],
            )

        elif tool_name == "get_vocabulary":
            limit = arguments.get("limit", 100)
            sort_by = arguments.get("sort_by", "id")
            ascending = arguments.get("ascending", True)
            phrases = self.db.get_vocabulary(limit=limit, sort_by=sort_by, ascending=ascending)
            if phrases:
                german_phrases = [p["german"] for p in phrases]
                phrases_list = "\n".join([f"- {german}" for german in german_phrases])
                result = f"Found {len(phrases)} phrase(s) in vocabulary:\n{phrases_list}"
            else:
                result = "No phrases in vocabulary"
            return ToolCallResult(result=result, terminal=False, user_outputs=[])

        return ToolCallResult(result="Unknown tool", terminal=True, user_outputs=[])

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history."""
        self.messages.append({"role": "assistant", "content": content})

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []

    def process_message(self, user_message: str) -> Generator[UserOutput, None, None]:
        """Process a user message and yield structured outputs as they appear."""
        self.add_user_message(user_message)

        input_list = []
        for msg in self.messages:
            input_list.append({"role": msg["role"], "content": msg["content"]})

        yield TypingOutput()

        response = self.client.responses.create(  # type: ignore
            model=self.model,
            instructions=self.system_prompt,
            input=input_list,
            tools=self.tools,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )

        max_iterations = 10
        iterations = 0
        review_shown_in_turn = False

        while response.status == "completed" and iterations < max_iterations:
            iterations += 1
            has_continuation_tools = False

            input_list += response.output

            # Process reasoning traces
            if self.enable_logs:
                for output_item in response.output:
                    if output_item.type == "reasoning" and output_item.content:
                        for content_item in output_item.content:
                            if content_item.type == "output_text":
                                yield LogOutput(message=f"Reasoning: {content_item.text}")

            for output_item in response.output:
                if output_item.type == "function_call":
                    tool_name = output_item.name
                    tool_args = json.loads(output_item.arguments)

                    if self.enable_logs:
                        args_str = ", ".join([f"{k}={str(v)[:20]}" for k, v in tool_args.items()])
                        yield LogOutput(message=f"Tool call: {tool_name}({args_str})")

                    tool_call_result = self._execute_tool(tool_name, tool_args)

                    # Handle user outputs from the tool
                    for user_output in tool_call_result.user_outputs:
                        # Only show one review per turn
                        if isinstance(user_output, ShowReviewOutput):
                            if not review_shown_in_turn:
                                yield user_output
                                review_shown_in_turn = True
                                if self.enable_logs:
                                    yield LogOutput(message=f"Showing review for phrase ID: {user_output.phrase_id}")
                            else:
                                if self.enable_logs:
                                    yield LogOutput(message="Additional review call skipped (only 1 per turn)")
                        else:
                            yield user_output

                    # Determine result string to send back to LLM
                    llm_result = tool_call_result.result
                    if isinstance(tool_call_result.user_outputs, list) and any(
                        isinstance(o, ShowReviewOutput) for o in tool_call_result.user_outputs
                    ):
                        if not review_shown_in_turn:
                            llm_result = tool_call_result.result
                        else:
                            llm_result = (
                                "Review NOT shown - only one review can be displayed per turn. This review was skipped."
                            )

                    input_list.append(
                        {"type": "function_call_output", "call_id": output_item.call_id, "output": llm_result}
                    )

                    # Only continue calling LLM for non-terminal tools
                    if not tool_call_result.terminal:
                        has_continuation_tools = True

            if not has_continuation_tools:
                break

            yield TypingOutput()

            response = self.client.responses.create(  # type: ignore
                model=self.model,
                instructions=self.system_prompt,
                input=input_list,
                tools=self.tools,
                reasoning={"effort": "minimal"},
                text={"verbosity": "low"},
            )

        response_text = ""
        for output_item in response.output:
            if output_item.type == "message":
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        response_text += content_item.text

        # Add assistant message to history
        if response_text:
            self.add_assistant_message(response_text)

        # Yield message output if there's any text
        if response_text:
            yield MessageOutput(message=response_text)
