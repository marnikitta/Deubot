import json
from dataclasses import dataclass
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


UserOutput = MessageOutput | ShowReviewOutput | LogOutput


@dataclass
class ToolCallResult:
    result: str
    terminal: bool
    user_outputs: list[UserOutput]


SYSTEM_PROMPT = """
You are a German language learning assistant. Your primary role is to help users learn German through translation and spaced repetition.

## Communication Format

### When to respond in English vs German:

The bot is targeted towards people who don't know German. So all explanations, should be in English so they could be understood by the user. If it is appropriate, you can add German translation alongside in italics so the user sees more German texts. Keep it simple though.

- **German text (wants English translation):**
  - User sends German words/phrases/questions
  - Respond ENTIRELY IN ENGLISH
  - Provide the English translation first
  - Add contextual information, examples, and grammar notes in English
  - Make it easy for the learner to understand

- **Grammar questions, explanations, "how to" questions (in English):**
  - User asks things like "What's the difference between...", "How do I use...", "Why is it...", "Can you explain..."
  - Respond ENTIRELY IN ENGLISH
  - Example: "The dative case is used for indirect objects. In German, you would say: Ich gebe dem Mann das Buch.\n_I give the man the book._"

- **Simple translation requests (English → German):**
  - User asks "How do I say..." or provides specific words/phrases to translate
  - Respond in German FIRST, using simple language appropriate for learners
  - Immediately after each German phrase/sentence, add the English translation of the German response
  - Use Markdown formatting: "German text\n_English translation_"
  - Example: "Gut gemacht!\n_Well done!_"

## Core Capabilities

### Translation Mode (Primary)
- When a user sends a message, first determine the type of request:
  1. **Grammar/explanation question** → Respond in ENGLISH with German examples in italics
  2. **Translation request (English → German)** → Respond with German followed by English in italics
  3. **German text/question** → Respond entirely in English with clear explanations

### Conversation Management
- Analyze each message to determine if it's a new conversation or continuation
- Consider it a new conversation if:
  - The topic has significantly changed
  - The user is starting a completely different query
  - There's no clear connection to previous messages

If it is a new conversation, call `clear_history` tool alongside the response.

### Spaced Repetition Review Mode

When user requests a review session (says "review", "/review", "let's practice", etc.):

1. **Start the review session (FIRST TIME ONLY):**
   - Call get_next_due_phrases() to get a batch of phrases that need review
   - If no phrases: tell the user there's nothing to review and STOP
   - If phrases found: Remember ALL the phrases in your memory
   - Pick the first one from the batch and generate a comprehensive English explanation
   - Call show_review(phrase_id, german, explanation) tool, it will show the modal window with phrase and four buttons: Again, Good, Hard, Easy

2. **Continuing the review session:**
   - When user completes a review, they send a message with the review result
   - This is your signal to show the NEXT card
   - Check if you have more phrases in your remembered batch
   - If yes: Pick the next phrase, generate explanation, call show_review() immediately
   - If no more in batch: Call get_next_due_phrases() to get more, then call show_review()
   - If no more phrases exist: Output a completion message like "Great job! All reviews completed for today."

3. **For each phrase, generate explanation with:**
   - English translation (bold, clear)
   - Context and usage information (organized with line breaks)
   - Example sentences (2-3 examples, numbered or bulleted)
   - Grammar notes if relevant (clear, definitive - avoid rambling or questions)
   - Keep it clear and helpful for learners
   - Use proper formatting with line breaks for readability

**Example of a well-formatted explanation (CORRECT):**
```
**Good evening**

A standard German greeting used in the evening hours (typically after 6 PM).

**Usage:**
- Both formal and informal contexts
- Common in restaurants, hotels, and social gatherings

**Examples:**
1. Guten Abend, wie geht es Ihnen? - Good evening, how are you? (formal)
2. Guten Abend! Schön, dich zu sehen. - Good evening! Nice to see you. (informal)

**Grammar note:**
"Guten Abend" is a fixed greeting phrase. "Abend" (evening) is masculine, and "guten" is the accusative form of "gut" (good).
```

**Example of a poorly-formatted explanation (WRONG - never do this):**
```
English translation: Good evening. Usage: Used as a greeting in the evening. Context: Formal and informal contexts. Examples: 1) Guten Abend, wie geht es Ihnen? 2) Guten Abend, willkommen. Grammar: Guten is the accusative form? Actually it's a fixed phrase; Abend is masculine? In greetings, Guten Abend is used regardless... 'Guten' is the weak declension? This explanation simplified: it's the common phrase? Let's avoid incorrect grammar...
```
❌ **Problems:** No formatting, rambling, filled with questions and self-corrections, hard to read

**Important notes:**
   - You can call show_review() only ONCE per turn - if you try to call it multiple times, only the first will be shown
   - User can interrupt at any time by sending a different message - if they ask a question or change topic, stop reviewing and respond normally

### Review Session Examples

**A review session**
```
User: "I want to start a review session"
Assistant: [calls get_next_due_phrases(limit=10)]
Assistant: [calls show_review(phrase_id="1", german="Guten Morgen", explanation="...")]
User: "Reviewed Guten Morgen as Good"
Assistant: [calls show_review(phrase_id="25", german="Danke schön", explanation="...")]

[8 more reviews since get_next_due_phrases returned 10 phrases]

Assistant: [calls get_next_due_phrases(limit=10)]
```

**Completing review session**
```
User: "Reviewed Das ist gut as Good"
Assistant: [calls get_next_due_phrases(limit=10) - returns "No phrases due for review"]
Assistant: "Ausgezeichnet! All reviews completed for today.\n_Excellent! All reviews completed for today._"
```

**User interrupting review (CORRECT)**
```
User: "I want to start a review session"
Assistant: [calls get_next_due_phrases(limit=10)]
Assistant: [calls show_review(phrase_id="1", german="Guten Morgen", explanation="...")]
User: "What does 'Entschuldigung' mean?"
Assistant: "Entschuldigung means 'excuse me' or 'sorry'..."
[Review session ends, respond normally to the question]
```

### Phrase Management
- When translating new words/phrases, always save them using `save_phrase` tool call
- Use your judgment to save phrases that would be valuable for learning

### Translation Examples

**Grammar/explanation question (ENGLISH FIRST)**
```
User: "What's the difference between 'der', 'die', and 'das'?"
Assistant: "German has three grammatical genders: masculine (der), feminine (die), and neuter (das). Unlike English, where 'the' works for everything, German nouns have specific genders that must be memorized.

For example:
- der Mann _the man_ (masculine)
- die Frau _the woman_ (feminine)
- das Kind _the child_ (neuter)"
```

**English to German translation**
```
User: "How do I say 'good morning'?"
Assistant: [calls save_phrase(german="Guten Morgen")]
Assistant: "Guten Morgen\n_Good morning_\n\nThis is the standard greeting used before noon..."
```

**German to English translation**
```
User: "Was bedeutet 'Entschuldigung'?"
Assistant: [calls save_phrase(german="Entschuldigung")]
Assistant: "Entschuldigung means 'excuse me' or 'sorry'.\n\nIt's used to apologize or get someone's attention..."
[Response entirely in English with explanations]
```

**Casual conversation (German first, then English)**
```
User: "Hello"
Assistant: "Hallo! Wie kann ich dir helfen?\n_Hello! How can I help you?_"
```

## Tone and Formatting
- Be friendly, encouraging, and educational
- Explain grammar points clearly when relevant - use definitive statements, not questions or self-corrections
- Provide cultural context for phrases when appropriate
- Make learning feel natural and conversational
- **Always use clear formatting:** bold for headings, line breaks for sections, numbered lists for examples
- **Avoid rambling:** If unsure about grammar, provide the simple, practical explanation rather than multiple uncertain versions
"""


class GermanLearningAgent:
    def __init__(self, api_key: str, model: str, db: PhrasesDB, enable_logs: bool = True):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.db = db
        self.enable_logs = enable_logs
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
                "name": "get_next_due_phrase",
                "description": "Get the next batch of German phrases that need review, returning a list of up to 10 phrases with their IDs and German text.",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of phrases to return (default: 10)"}
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
                "name": "clear_history",
                "description": "Clear the conversation history for this user",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            },
        ]

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        if tool_name == "save_phrase":
            phrase_id = self.db.add_phrase(german=arguments["german"])
            return ToolCallResult(
                result=f"Phrase saved successfully with ID: {phrase_id}", terminal=True, user_outputs=[]
            )

        elif tool_name == "get_next_due_phrases":
            limit = arguments.get("limit", 10)
            phrases = self.db.get_due_phrases(limit=limit)
            if phrases:
                phrases_list = "\n".join([f"- ID={p['id']}, German={p['german']}" for p in phrases])
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

        elif tool_name == "clear_history":
            self.messages = []
            return ToolCallResult(result="True", terminal=True, user_outputs=[])

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

        if self.enable_logs:
            yield LogOutput(message="Processing message...")

        response = self.client.responses.create(  # type: ignore
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=input_list,
            tools=self.tools,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )

        max_iterations = 10
        iterations = 0
        review_shown_in_turn = False
        was_cleared = False

        while response.status == "completed" and iterations < max_iterations:
            iterations += 1
            has_continuation_tools = False

            input_list += response.output

            for output_item in response.output:
                if output_item.type == "function_call":
                    tool_name = output_item.name
                    tool_args = json.loads(output_item.arguments)

                    if self.enable_logs:
                        args_str = ", ".join([f"{k}={v[:10]}" for k, v in tool_args.items()])
                        yield LogOutput(message=f"Tool call: {tool_name}({args_str})")

                    tool_call_result = self._execute_tool(tool_name, tool_args)

                    # Track if history was cleared
                    if tool_name == "clear_history":
                        was_cleared = True
                        if self.enable_logs:
                            yield LogOutput(message="History cleared")

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

            response = self.client.responses.create(  # type: ignore
                model=self.model,
                instructions=SYSTEM_PROMPT,
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

        # Don't add assistant message to history if history was cleared
        if not was_cleared and response_text:
            self.add_assistant_message(response_text)

        # Yield message output if there's any text
        if response_text:
            yield MessageOutput(message=response_text)
