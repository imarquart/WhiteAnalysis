import html
from typing import List

from whiteanalysis.prompts import Insights


def generate_insights_report(
    responses: List[Insights],
    filename: str,
    case: str,
    model: str,
    output_path: str = "insights_report.html",
):
    """
    Generate an HTML report from a list of Insights objects.

    Args:
        responses: List of Insights objects
        filename: Source filename
        case: Case description
        model: Model name
        output_path: Path where the HTML file will be saved
    """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Case Study Quotes</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
                padding-bottom: 10px;
            }}
            .meta-info {{
                color: #666;
                font-size: 0.9em;
            }}
            .insight-container {{
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .context-box {{
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #4a90e2;
                margin-bottom: 20px;
            }}
            .quote-box {{
                background-color: #fff;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-bottom: 15px;
            }}
            .quote-text {{
                font-style: italic;
                color: #2c3e50;
                border-left: 3px solid #4a90e2;
                padding-left: 10px;
                margin: 10px 0;
            }}
            .quote-position {{
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }}
            .quote-relation {{
                background-color: #f0f7ff;
                padding: 10px;
                border-radius: 4px;
                margin-top: 10px;
            }}
            h2, h3 {{
                color: #2c3e50;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Cases and Quotes</h1>
            <div class="meta-info">
                <p><strong>Source File:</strong> {html.escape(filename)}</p>
                <p><strong>Model:</strong> {html.escape(model)}</p>
            </div>
        </div>
    """

    for i, insight in enumerate(responses, 1):
        html_content += f"""
        <div class="insight-container">
            <h2>Insight Set {i}</h2>
            
            <div class="context-box">
                <h3>General Context</h3>
                <p>{html.escape(insight.general_context)}</p>
                <h3>Relevance</h3>
                <p>{html.escape(insight.general_relation)}</p>
            </div>
            
            <h3>Extracted Quotes</h3>
        """

        for quote in insight.quotes:
            html_content += f"""
            <div class="quote-box">
                <p><strong>{html.escape(quote.text)}</strong> </p>
                <div class="quote-context">{html.escape(quote.context)}</div>
                <div class="quote-position"><strong>Position:</strong> {html.escape(quote.position)}</div>
                <div class="quote-issue_in_draft"><strong>Issue in Draft:</strong> {html.escape(quote.issue_in_draft if hasattr(quote, 'issue_in_draft') else "")}</div>
                <div class="quote-relation">
                    <strong>Relevance:</strong> {html.escape(quote.relation)}
                </div>
            </div>
            """

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
