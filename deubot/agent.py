import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from openai import OpenAI

from deubot.database import PhrasesDB
from deubot.tools import get_tools
from deubot.translations import TranslationService

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
    needs_llm_followup: bool
    user_outputs: list[UserOutput]


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text()


class GermanLearningAgent:
    def __init__(self, api_key: str, model: str, light_model: str, db: PhrasesDB, enable_logs: bool = False):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.light_model = light_model
        self.db = db
        self.enable_logs = enable_logs
        self.system_prompt = _load_system_prompt()
        self.messages: list[dict[str, str]] = []
        self.tools = get_tools()
        self.translation_service = TranslationService(self.client, light_model)

    def _execute_save_phrases(self, arguments: dict[str, Any]) -> ToolCallResult:
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

        if len(phrases) == 1:
            result = f"Phrase saved successfully with ID: {saved_ids[0]}"
        else:
            result = f"{len(phrases)} phrases saved successfully with IDs: {', '.join(saved_ids)}"

        return ToolCallResult(
            result=result,
            needs_llm_followup=True,
            user_outputs=[MessageOutput(message=user_message)],
        )

    def _execute_start_review(self) -> ToolCallResult:
        phrases = self.db.get_due_phrases(limit=20)
        if not phrases:
            logger.info("No phrases due for review")
            return ToolCallResult(result="No phrases due for review", needs_llm_followup=True, user_outputs=[])

        logger.info(f"Starting review session with {len(phrases)} phrases")
        cards = self.translation_service.get_translation_cards_parallel(phrases)
        review_outputs = [
            ShowReviewOutput(phrase_id=card.phrase_id, german=card.german, explanation=card.explanation)
            for card in cards
        ]

        return ToolCallResult(
            result=f"Review session started with {len(cards)} phrases. Bot will handle reviews locally.",
            needs_llm_followup=False,
            user_outputs=[ShowReviewBatchOutput(reviews=review_outputs)],
        )

    def _execute_get_vocabulary(self, arguments: dict[str, Any]) -> ToolCallResult:
        limit = arguments.get("limit", 100)
        sort_by = arguments.get("sort_by", "id")
        ascending = arguments.get("ascending", True)
        phrases = self.db.get_vocabulary(limit=limit, sort_by=sort_by, ascending=ascending)
        if phrases:
            phrases_list = "\n".join(
                [f"- ID: {p['id']}, German: {p['german']}, Ease: {p['ease_factor']:.1f}" for p in phrases]
            )
            result = f"Found {len(phrases)} phrase(s) in vocabulary:\n{phrases_list}"
            logger.info(f"Retrieved {len(phrases)} phrases from vocabulary (sort_by={sort_by}, ascending={ascending})")
        else:
            result = "No phrases in vocabulary"
            logger.info("No phrases in vocabulary")
        return ToolCallResult(result=result, needs_llm_followup=True, user_outputs=[])

    def _execute_remove_phrases(self, arguments: dict[str, Any]) -> ToolCallResult:
        phrase_ids = arguments["phrase_ids"]
        if not isinstance(phrase_ids, list):
            phrase_ids = [phrase_ids]

        phrases_to_remove = []
        for phrase_id in phrase_ids:
            if phrase_id in self.db.phrases:
                phrases_to_remove.append((phrase_id, self.db.phrases[phrase_id].german))

        removed_ids, not_found_ids = self.db.remove_phrases(phrase_ids)

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
                user_message_parts.append(f"⚠ {len(not_found_ids)} phrase IDs not found: {', '.join(not_found_ids)}")

        user_message = "\n".join(user_message_parts)

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
            needs_llm_followup=True,
            user_outputs=[MessageOutput(message=user_message)],
        )

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        match tool_name:
            case "save_phrases":
                return self._execute_save_phrases(arguments)
            case "start_review":
                return self._execute_start_review()
            case "get_vocabulary":
                return self._execute_get_vocabulary(arguments)
            case "remove_phrases":
                return self._execute_remove_phrases(arguments)
            case _:
                return ToolCallResult(result="Unknown tool", needs_llm_followup=False, user_outputs=[])

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

    def _extract_text(self, response, item_type: str) -> str:
        """Extract text from response output items of given type (e.g., 'reasoning', 'message')."""
        texts = []
        for output_item in response.output:
            if output_item.type == item_type and hasattr(output_item, "content") and output_item.content:
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        texts.append(content_item.text)
        return "".join(texts)

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

            if self.enable_logs:
                reasoning_text = self._extract_text(response, "reasoning")
                if reasoning_text:
                    yield LogOutput(message=f"Reasoning: {reasoning_text}")

            for output_item in response.output:
                if output_item.type != "function_call":
                    continue

                tool_name = output_item.name
                tool_args = json.loads(output_item.arguments)

                if self.enable_logs:
                    args_str = ", ".join([f"{k}={str(v)[:20]}" for k, v in tool_args.items()])
                    yield LogOutput(message=f"Tool call: {tool_name}({args_str})")

                tool_call_result = self._execute_tool(tool_name, tool_args)
                yield from tool_call_result.user_outputs

                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": output_item.call_id,
                        "output": tool_call_result.result,
                    }
                )

                if tool_call_result.needs_llm_followup:
                    has_continuation_tools = True

            if has_continuation_tools:
                yield TypingOutput()
                response = self._call_llm(input_list, iteration=iterations + 1)
            else:
                break

        self.messages = input_list

        response_text = self._extract_text(response, "message")
        if response_text:
            yield MessageOutput(message=response_text)
