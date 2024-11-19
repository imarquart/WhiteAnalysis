import os

import instructor
from dotenv import load_dotenv
from instructor import Instructor
from openai import OpenAI


def return_client() -> tuple[Instructor, OpenAI]:
    """Returns both Instructor and OpenAI client objects."""
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    iclient = instructor.from_openai(client=client)
    return iclient, client
