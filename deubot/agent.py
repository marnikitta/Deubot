import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from openai import OpenAI

from deubot.database import PhrasesDB
from deubot.tools import get_tools

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent parsing errors."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class MessageOutput:
    message: str


@dataclass
class ShowReviewOutput:
    phrase_id: str
    german: str
    explanation: str


@dataclass
class ShowReviewBatchOutput:
    reviews: list[ShowReviewOutput]


@dataclass
class LogOutput:
    message: str


@dataclass
class TypingOutput:
    pass


UserOutput = MessageOutput | ShowReviewOutput | ShowReviewBatchOutput | LogOutput | TypingOutput


@dataclass
class ToolCallResult:
    result: str
    terminal: bool
    user_outputs: list[UserOutput]


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text()


class GermanLearningAgent:
    def __init__(self, api_key: str, model: str, db: PhrasesDB, enable_logs: bool = False):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.db = db
        self.enable_logs = enable_logs
        self.system_prompt = _load_system_prompt()
        self.messages: list[dict[str, str]] = []
        self.tools = get_tools()

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        if tool_name == "save_phrases":
            phrases = arguments["phrases"]
            if not isinstance(phrases, list):
                phrases = [phrases]

            saved_ids = []
            new_phrases = []
            duplicate_phrases = []

            for german in phrases:
                phrase_id, is_new, existing_german = self.db.add_phrase(german=german)
                saved_ids.append(phrase_id)

                if is_new:
                    new_phrases.append(german)
                    logger.info(f"Saved new phrase '{german}' with ID {phrase_id}")
                else:
                    duplicate_phrases.append((german, existing_german))
                    logger.info(f"Phrase '{german}' already exists as '{existing_german}' with ID {phrase_id}")

            # Generate user message based on what was saved
            user_message_parts = []

            if new_phrases:
                if len(new_phrases) == 1:
                    user_message_parts.append(f"✓ Saved: <b>{escape_html(new_phrases[0])}</b>")
                else:
                    escaped_phrases = ", ".join(escape_html(p) for p in new_phrases[:5])
                    suffix = "..." if len(new_phrases) > 5 else ""
                    user_message_parts.append(f"✓ Saved {len(new_phrases)} phrases: <b>{escaped_phrases}</b>{suffix}")

            if duplicate_phrases:
                for user_phrase, existing_phrase in duplicate_phrases:
                    assert existing_phrase is not None
                    if user_phrase.lower() == existing_phrase.lower():
                        user_message_parts.append(f"Already saved: <b>{escape_html(existing_phrase)}</b>")
                    else:
                        user_message_parts.append(
                            f"Already saved: <b>{escape_html(existing_phrase)}</b> "
                            f"(you entered: {escape_html(user_phrase)})"
                        )

            user_message = "\n".join(user_message_parts)

            # Result message for the agent (no difference for agent)
            if len(phrases) == 1:
                result = f"Phrase saved successfully with ID: {saved_ids[0]}"
            else:
                result = f"{len(phrases)} phrases saved successfully with IDs: {', '.join(saved_ids)}"

            return ToolCallResult(
                result=result,
                terminal=False,
                user_outputs=[MessageOutput(message=user_message)],
            )

        elif tool_name == "get_next_due_phrases":
            limit = min(arguments.get("limit", 30), 100)
            phrases = self.db.get_due_phrases(limit=limit)
            if phrases:
                phrases_list = "\n".join([f"- ID: {p['id']}, German: {p['german']}" for p in phrases])
                result = f"Found {len(phrases)} phrase(s) due for review:\n{phrases_list}"
                logger.info(f"Retrieved {len(phrases)} due phrases (limit={limit})")
            else:
                result = "No phrases due for review"
                logger.info("No phrases due for review")
            return ToolCallResult(result=result, terminal=False, user_outputs=[])

        elif tool_name == "show_review_batch":
            reviews = arguments["reviews"]
            review_outputs = [
                ShowReviewOutput(
                    phrase_id=r["phrase_id"],
                    german=r["german"],
                    explanation=r["explanation"],
                )
                for r in reviews
            ]
            logger.info(f"Showing batch of {len(reviews)} reviews")
            return ToolCallResult(
                result=f"Batch of {len(reviews)} reviews sent to user. Bot will handle reviews locally and send 'All reviews completed' when finished.",
                terminal=True,
                user_outputs=[ShowReviewBatchOutput(reviews=review_outputs)],
            )

        elif tool_name == "get_vocabulary":
            limit = arguments.get("limit", 100)
            sort_by = arguments.get("sort_by", "id")
            ascending = arguments.get("ascending", True)
            phrases = self.db.get_vocabulary(limit=limit, sort_by=sort_by, ascending=ascending)
            if phrases:
                phrases_list = "\n".join(
                    [f"- ID: {p['id']}, German: {p['german']}, Ease: {p['ease_factor']:.1f}" for p in phrases]
                )
                result = f"Found {len(phrases)} phrase(s) in vocabulary:\n{phrases_list}"
                logger.info(
                    f"Retrieved {len(phrases)} phrases from vocabulary (sort_by={sort_by}, ascending={ascending})"
                )
            else:
                result = "No phrases in vocabulary"
                logger.info("No phrases in vocabulary")
            return ToolCallResult(result=result, terminal=False, user_outputs=[])

        elif tool_name == "remove_phrases":
            phrase_ids = arguments["phrase_ids"]
            if not isinstance(phrase_ids, list):
                phrase_ids = [phrase_ids]

            # Get phrase details before removing
            phrases_to_remove = []
            for phrase_id in phrase_ids:
                if phrase_id in self.db.phrases:
                    phrases_to_remove.append((phrase_id, self.db.phrases[phrase_id].german))

            removed_ids, not_found_ids = self.db.remove_phrases(phrase_ids)

            # Generate user message based on what was removed
            user_message_parts = []

            if removed_ids:
                if len(removed_ids) == 1:
                    removed_german = next(german for pid, german in phrases_to_remove if pid == removed_ids[0])
                    user_message_parts.append(f"✗ Removed: <b>{escape_html(removed_german)}</b> (ID: {removed_ids[0]})")
                else:
                    user_message_parts.append(f"✗ Removed {len(removed_ids)} phrases:")
                    for phrase_id in removed_ids[:5]:
                        removed_german = next(german for pid, german in phrases_to_remove if pid == phrase_id)
                        user_message_parts.append(f"  - <b>{escape_html(removed_german)}</b> (ID: {phrase_id})")
                    if len(removed_ids) > 5:
                        user_message_parts.append(f"  ... and {len(removed_ids) - 5} more")

            if not_found_ids:
                if len(not_found_ids) == 1:
                    user_message_parts.append(f"⚠ Phrase ID {not_found_ids[0]} not found")
                else:
                    user_message_parts.append(
                        f"⚠ {len(not_found_ids)} phrase IDs not found: {', '.join(not_found_ids)}"
                    )

            user_message = "\n".join(user_message_parts)

            # Result message for the agent
            if len(removed_ids) == 1:
                result = f"Phrase {removed_ids[0]} removed successfully"
            elif removed_ids:
                result = f"{len(removed_ids)} phrases removed successfully: {', '.join(removed_ids)}"
            else:
                result = "No phrases were removed (all IDs not found)"

            if not_found_ids:
                result += f". {len(not_found_ids)} ID(s) not found: {', '.join(not_found_ids)}"

            return ToolCallResult(
                result=result,
                terminal=False,
                user_outputs=[MessageOutput(message=user_message)],
            )

        return ToolCallResult(result="Unknown tool", terminal=True, user_outputs=[])

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []

    def _call_llm(self, input_list: list[dict], iteration: int):
        """Call the LLM API and log statistics."""
        response = self.client.responses.create(  # type: ignore
            model=self.model,
            instructions=self.system_prompt,
            input=input_list,
            tools=self.tools,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )

        # Log API call stats
        has_reasoning = any(item.type == "reasoning" for item in response.output)
        tool_calls = [item.name for item in response.output if item.type == "function_call"]
        tool_calls_str = f", tool_calls=[{', '.join(tool_calls)}]" if tool_calls else ""
        reasoning_str = ", with reasoning" if has_reasoning else ""
        logger.info(
            f"GPT API call completed (iteration {iteration}){reasoning_str}{tool_calls_str}, "
            f"input_tokens={getattr(response.usage, 'input_tokens', 'N/A')}, "
            f"output_tokens={getattr(response.usage, 'output_tokens', 'N/A')}"
        )

        return response

    def process_message(self, user_message: str) -> Generator[UserOutput, None, None]:
        """Process a user message and yield structured outputs as they appear."""
        input_list = list(self.messages)
        input_list.append({"role": "user", "content": user_message})

        yield TypingOutput()

        response = self._call_llm(input_list, iteration=1)

        max_iterations = 10
        iterations = 0

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
                        yield user_output

                    input_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": output_item.call_id,
                            "output": tool_call_result.result,
                        }
                    )

                    # Only continue calling LLM for non-terminal tools
                    if not tool_call_result.terminal:
                        has_continuation_tools = True

            if not has_continuation_tools:
                break

            yield TypingOutput()

            response = self._call_llm(input_list, iteration=iterations + 1)

        response_text = ""
        for output_item in response.output:
            if output_item.type == "message":
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        response_text += content_item.text

        # Save the entire conversation including tool calls and outputs to history
        self.messages = input_list

        # Yield message output if there's any text
        if response_text:
            yield MessageOutput(message=response_text)
