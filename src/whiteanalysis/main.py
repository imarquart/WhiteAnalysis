import json
import os
import re
import time
from io import BytesIO
from typing import Dict, List

import structlog
import tenacity
import tiktoken
import typer
from tqdm.auto import tqdm

from whiteanalysis.html_creation import generate_insights_report
from whiteanalysis.paper import py_cases
from whiteanalysis.pdf_handling import (
    PDFDocument,
    get_content_from_pdf,
    get_content_from_unstructured,
)
from whiteanalysis.prompts import (
    Insights,
    create_batched_prompts,
    create_full_paper_prompts,
)
from whiteanalysis.utils import return_client
from whiteanalysis.word_creation import generate_word_report

app = typer.Typer()
logger = structlog.get_logger()


def clean_json_string(text):
    """
    Clean a JSON string by:
    1. Replacing curly quotes with straight quotes
    2. Removing invisible characters
    3. Escaping line breaks
    4. Escaping backslashes
    """
    # Replace curly quotes with straight quotes
    text = text.replace('"', '"').replace('"', '"')

    # Remove invisible characters and other problematic Unicode
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)

    # Replace multiple spaces with single space
    text = re.sub(r"\s+", " ", text)

    # Escape backslashes
    text = text.replace("\\", "\\\\")

    # Escape line breaks
    text = text.replace("\n", "\\n")

    return text


@tenacity.retry(
    wait=tenacity.wait_exponential(min=1, max=60),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type((Exception)),
)
def run_full_page(
    pages: List[PDFDocument], case_text: str, encodings: tiktoken.Encoding, model: str
) -> List[Insights]:
    """Run analysis on full document pages.

    Args:
        pages: List of PDFDocument objects containing page content
        case_text: The case text to analyze against
        encodings: Tokenizer encoding
        model: Model identifier to use

    Returns:
        List of Insights objects containing analysis results

    Raises:
        Exception: If API call fails after retries
    """
    iclient, _ = return_client()
    responses = []

    try:
        full_page_prompts = create_full_paper_prompts(
            pages, case_text, encodings=encodings
        )
        token_count = sum(
            len(encodings.encode(x["content"])) for x in full_page_prompts
        )
        logger.debug(f"Tokens in prompts: {token_count}")

        response = iclient.create(
            messages=full_page_prompts, response_model=Insights, model=model
        )
        responses.append(response)
        time.sleep(60)
        return responses

    except Exception as e:
        logger.exception("Error running full page analysis", error=str(e))
        raise


@tenacity.retry(
    wait=tenacity.wait_exponential(min=1, max=60),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type((Exception)),
)
def run_single_batch(
    prompt: List[Dict], encodings: tiktoken.Encoding, model: str
) -> Insights:
    """Run analysis on a single batch of prompts.

    Args:
        prompt: List of prompt dictionaries
        encodings: Tokenizer encoding
        model: Model identifier to use

    Returns:
        Insights object containing analysis results

    Raises:
        Exception: If API call fails after retries
    """
    iclient, _ = return_client()
    try:
        token_count = sum(len(encodings.encode(x["content"])) for x in prompt)
        logger.debug(f"Tokens in prompts: {token_count}")

        response = iclient.create(messages=prompt, response_model=Insights, model=model)
        return response

    except Exception as e:
        logger.exception("Error running batch analysis", error=str(e))
        raise


def run_batched_prompts(
    pages: List[PDFDocument],
    case_text: str,
    encodings: tiktoken.Encoding,
    model: str,
) -> List[Insights]:
    """Run analysis on batched prompts for large documents.

    Args:
        pages: List of PDFDocument objects
        case_text: The case text to analyze against
        encodings: Tokenizer encoding
        model: Model identifier to use

    Returns:
        List of Insights objects containing analysis results
    """
    responses = []
    prompt_batch_size = 64000

    try:
        prompt_batches = create_batched_prompts(
            pages, case_text, prompt_batch_size, encodings
        )

        with tqdm(
            prompt_batches,
            desc="Processing prompt batches",
            unit="batch",
            leave=False,
        ) as pbar:
            for batch in pbar:
                response = run_single_batch(batch, encodings, model)
                responses.append(response)
                time.sleep(30)

        return responses

    except Exception as e:
        logger.exception("Error running batched prompts", error=str(e))
        return responses


def process_document(
    filename: str,
    cases: Dict[str, str],
    encodings: tiktoken.Encoding,
    model: str,
    output_folder: str,
) -> None:
    """Process a single document file.

    Args:
        filename: Path to the document file
        cases: Dictionary of cases to analyze
        encodings: Optional tokenizer encoding
        model: Model identifier to use
        output_folder: Base output folder path
    """
    logger.debug(f"Processing file: {filename}")

    try:
        with open(filename, "rb") as file:
            fileio = BytesIO(file.read())

        pages = get_content_from_pdf(fileio, filename)
        total_length = (
            sum(len(encodings.encode(x.text)) for x in pages) if encodings else 0
        )

        if total_length <= 100:
            logger.debug(f"Using unstructured extraction for {filename}")
            unst_pages = get_content_from_unstructured(filename)
            pages = [
                PDFDocument(
                    page=i + 1,
                    text=unst_page.text,
                    filename=filename,
                )
                for i, unst_page in enumerate(unst_pages)
            ]

        file_base = os.path.splitext(os.path.basename(filename))[0].replace(" ", "")
        folder = os.path.join(output_folder, model, file_base)
        os.makedirs(folder, exist_ok=True)

        for case_name, case_text in tqdm(
            cases.items(), desc="Processing cases", leave=False
        ):
            logger.debug(f"Processing case: {case_name}")
            total_length = sum(len(encodings.encode(x.text)) for x in pages)  # type: ignore

            responses = (
                run_full_page(pages, case_text, encodings, model)
                if total_length < 64000
                else run_batched_prompts(pages, case_text, encodings, model)
            )

            output_base = f"{case_name}_{file_base}"
            output_html = os.path.join(folder, f"{output_base}.html")
            output_docx = os.path.join(folder, f"{output_base}.docx")

            generate_insights_report(
                responses=responses,
                filename=filename,
                case=case_text,
                model=model,
                output_path=output_html,
            )
            generate_word_report(
                responses=responses,
                filename=filename,
                case=case_text,
                model=model,
                output_path=output_docx,
            )

    except Exception as e:
        logger.exception(f"Error processing document {filename}", error=str(e))


@app.command()
def run_analysis(
    document_folder: str = "documents",
    output_folder: str = "output",
    inputs: str = "inputs/cases.json",
    model: str = "gpt-4o-mini",
    add_timestamp: bool = True,
) -> None:
    """Run analysis on a folder of documents.

    Args:
        document_folder: Folder containing PDF documents
        output_folder: Folder for output files
        inputs: JSON file containing cases
        model: Model identifier to use
    """
    try:
        filenames = [
            os.path.join(document_folder, x)
            for x in os.listdir(document_folder)
            if x.lower().endswith(".pdf")
        ]

        with open(inputs, "r", encoding="utf-8") as f:
            try:
                cleaned = clean_json_string(f.read())
                cases = json.loads(cleaned)
            except Exception:
                cases = py_cases

        if add_timestamp:
            output_folder = os.path.join(output_folder, time.strftime("%y%m%d%M"))

        try:
            encodings = tiktoken.encoding_for_model(model)
        except Exception as e:
            logger.exception("Error loading tokenizer", model=model, error=str(e))
            encodings = None

        with tqdm(filenames, desc="Processing files", unit="file", leave=True) as pbar:
            for filename in pbar:
                process_document(filename, cases, encodings, model, output_folder)

        logger.info("Analysis complete")

    except Exception as e:
        logger.exception("Error in run_analysis", error=str(e))
        raise typer.Exit(code=1)


def run() -> None:
    """Entry point for the application."""
    app()


if __name__ == "__main__":
    run()
