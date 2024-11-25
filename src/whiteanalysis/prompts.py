from copy import deepcopy

import structlog
import tiktoken
from pydantic import BaseModel, Field

from whiteanalysis.pdf_handling import PDFDocument

logger = structlog.get_logger()


class Quote(BaseModel):
    """Extract quotes using this tool, ensuring verbatim and correct referencing so
    the scientific process is in order.

    Make sure to relate the quote to a specific argument and line in the draft.
    Make sure to give the text of the quote verbatim."""

    context: str = Field(..., title="Context of the quote within the document.")
    position: str = Field(
        ...,
        title="Where the quote is located in the source (if given). Example: Page 3, Paragraph 2 or Page 5, Line 4, or Page 4, Middle",
    )
    text: str = Field(..., title="Verbatim text of the quote")
    issue_in_draft: str = Field(
        ...,
        description="The exact argument in the draft that the quote might help support. Try to focus on a precise point in the text and give some verbatim quote so we can find it.",
    )
    relation: str = Field(
        ...,
        title="How the quote supports the argument or helps to solve the issue presented, relating it from the source document to the drafts's context",
    )


class Quote_case(BaseModel):
    """Extract quotes address the issue.
    Make sure to relate the quote to the issues's context.
    Make sure to copy the text of the quote verbatim."""

    context: str = Field(..., title="Context of the quote within the document.")
    position: str = Field(
        ...,
        title="Where the quote is located in the document (if given). Example: Page 3, Paragraph 2 or Page 5, Line 4, or Page 4, Middle",
    )
    text: str = Field(..., title="Verbatim text of the quote")
    relation: str = Field(
        ...,
        title="How the quote might provde guidance to solve the issue, relating it from the source document to the person's context",
    )


class Insights(BaseModel):
    """Given a a draft and a scientific source document, use this tool to extract insights in forms of quotes
    that support the arguments presented and hence help a hypothetical person address the given issue presented in the draft.

    The scientific source documents treat social relationships and social structure on
    a scientific level. The source might describe mechanisms, patterns or action
    either on an abstract level or in a specific context.

    The draft is for an article giving insights and guidance based
    on the works of HC White, the source documents' author. Therefore, you might need to translate
    the insights of White to the draft's arguments.

    You must find insights that support the arguments made in the draft, and add
    further insights to offer new arguments, sharpen ones, or better represent White's work.
    Be precise in how you refer to either source or draft, but try to provide as many insights as you can."""

    general_context: str = Field(..., title="General context in the source document")
    general_relation: str = Field(
        ...,
        title="How the general context might help the person (or not if it doesn't)",
    )
    quotes: list[Quote] = Field(..., title="List of quotes extracted from the document")


class Insights_case(BaseModel):
    """Given a source document, you must extract insights in forms of quotes
    that might help the person address the given issue presented in the paper.
    The source documents treat social relationships and social structure on
    a scientific level. The source might describe mechanisms, patterns or action
    either on an abstract level or in a specific context.

    The issue might be situated in a different context.
    Yet, the insights from the source document might be useful to address the issue.
    Therefore, you are required to translate the insights to the person's context.

    The material will be used for an article giving insights and guidance based
    on the works of HC White, the source documents' author.

    Give as many quotes as you can find that might help address the issue.

    Try to provide quotes that are actionable or can be used as guidance.
    Another type of quotes might be ones that are insightful, clever or thought-provoking for
    a general practicioners article on White.

    If there are no insights, you can leave the fields empty."""

    general_context: str = Field(..., title="General context of the source document")
    general_relation: str = Field(
        ...,
        title="How the general context might help the person (or not if it doesn't)",
    )
    quotes: list[Quote] = Field(..., title="List of quotes extracted from the document")


system_prompt_case = [
    {
        "content": """\
Given parts of a source document, help a person navigate their social environment and solve an issue
as described below. You must extract insights using the tools provided.
Next to the focal content, you might be given more context to help you extract insights.
Extract insights only from the focal content.
If there are no insights, you can leave the fields empty.\n\n""",
        "role": "system",
    }
]
system_prompt = [
    {
        "content": """\
You are given the draft of an academic paper that
makes an argument for using the academic work of the late HC White, our co-author, in a business context.
Your task is to extract insights to support the existing arguments in the paper.
You can also extract insights to offer new perspectives or arguments we might have missed.
Use the provided tools to do so.
If there are no insights, you can leave the fields empty.\n\n""",
        "role": "system",
    }
]


def return_pages(pages: list[PDFDocument], focal_page_number: int, range: int):
    """Returns prompt with the focal page as context and
    range of pages before and after.
    Range is the number of pages to show before and after the focal page."""
    focal_page = [page for page in pages if page.page == focal_page_number][0]
    pages_before = [page for page in pages if page.page < focal_page_number][-range:]
    pages_after = [page for page in pages if page.page > focal_page_number][:range]
    return focal_page, pages_before, pages_after


def create_prompts(
    pages: list[PDFDocument], focal_page_number: int, range: int, issue: str
):
    """Creates prompts with the focal page as context and
    range of pages before and after.
    Range is the number of pages to show before and after the focal page."""
    focal_page, pages_before, pages_after = return_pages(
        pages, focal_page_number, range
    )

    prompts = system_prompt
    context_before = "\n".join([f"Page:{x['page']}\n{x['text']}" for x in pages_before])
    context_after = "\n".join([f"Page:{x['page']}\n{x['text']}" for x in pages_after])
    prompts.append(
        {
            "content": "<CONTEXT BEFORE FOCAL PAGE> \n"
            + context_before
            + "</CONTEXT BEFORE FOCAL PAGE>\n",
            "role": "system",
        }
    )
    prompts.append(
        {
            "content": "<FOCAL PAGE> \n" + focal_page.text + "</FOCAL PAGE>\n",
            "role": "system",
        }
    )
    prompts.append(
        {
            "content": "<CONTEXT AFTER FOCAL PAGE> \n"
            + context_after
            + "</CONTEXT AFTER FOCAL PAGE>\n",
            "role": "system",
        }
    )
    prompts.append({"content": "<ISSUE> \n" + issue + "\n", "role": "user"})
    return prompts


def return_system_tokens(issue, encodings: tiktoken.Encoding):
    """Returns the number of tokens in the system prompts."""
    return len(encodings.encode(str(system_prompt[0]["content"]))) + len(
        encodings.encode(str(issue))
    )


def create_batched_prompts(pages: list[PDFDocument], issue, page_batch_size, encodings):
    """Creates prompts with a batch of pages as context."""
    prompts_list = []
    current_context = ""
    logger.debug(f"System prompts tokens {return_system_tokens(issue,encodings)}")
    logger.debug(f"Creating prompts for {len(pages)} pages")
    for i, page in enumerate(pages):
        current_tokens = len(encodings.encode(current_context))
        new_tokens = len(encodings.encode(page.text))
        if current_tokens + new_tokens > page_batch_size:
            logger.debug(
                f"Page {i}: Tokens for current context: {current_tokens}, tokens for new page: {new_tokens}"
            )
            prompts = deepcopy(system_prompt)
            prompts.append(
                {"content": "<DRAFT> \n" + issue + "</DRAFT>\n", "role": "user"}
            )
            prompts.append(
                {
                    "content": "<CONTEXT> \n" + current_context + "</CONTEXT>\n",
                    "role": "system",
                }
            )
            prompts_list.append(prompts)
            current_context = page.text
        else:
            current_context += page.text
    return prompts_list


def create_full_paper_prompts(pages, issue, encodings):
    """Creates prompts with the full paper as context."""
    logger.debug(f"System prompts tokens {return_system_tokens(issue,encodings)}")
    prompts = deepcopy(system_prompt)
    prompts.append({"content": "<DRAFT> \n" + issue + "</DRAFT>\n", "role": "user"})
    for page in pages:
        prompts.append(
            {"content": "<PAGE> \n" + page.text + "</PAGE>\n", "role": "system"}
        )
    return prompts
