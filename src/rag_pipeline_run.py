import os, json, base64
import streamlit as st
from .rag_retrieve import get_topk_reviews
from .rag_llm_summarise import summarise_reference
from .review_prompts import REVIEWER_PROMPT, ACTION_PROMPT


def run_pipeline(client, target_title, target_abstract, text_summary, merged_image_path, k):
    
    status_placeholder = st.empty()

    # Step 2
    status_placeholder.write("[Step 2] Retrieving similar manuscripts...")
    print(f"[Step 2] Retrieving similar manuscripts (k={k})...")

    reviews = get_topk_reviews(target_title, target_abstract, k=k)
    print(f" found {len(reviews)} similar review")

    # Clear Step 1 message
    status_placeholder.empty() 

    # Step 3
    status_placeholder.write("[Step 3] Generating reference summary...")
    print(f"[Step 3] Generating reference summary...")

    summary_json = summarise_reference(client, target_title, reviews)
    reference_summary = json.loads(summary_json)

    # Clear Step 2 message
    status_placeholder.empty()

    # Step 4
    status_placeholder.write("[Step 4] Generating RAG-based multimodal review...")
    print(f"[Step 4] Generating RAG-based multimodal review...")

    with open(merged_image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    rag_prompt = f"""
    Below is the target paper to be reviewed, including both a text summary and screenshots of each page.
    Use the reference review only as guidance and do not copy or paraphrase it directly.

    Paper summary:
    {text_summary}

    Reference review (summary):
    {reference_summary}
    """

    review_messages = [
        {"role": "system", "content": REVIEWER_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": rag_prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"}
        ]}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=review_messages,
        temperature=0.3,
        max_tokens=4000
    )

    rag_review = response.choices[0].message.content.strip()

    # Clear Step 3 message
    status_placeholder.empty()

    # Step 4
    status_placeholder.write("[Step 5] Generating actionable to-do list...")
    print(f"[Step 5] Generating actionable to-do list...")

    todo_prompt = f"""
    Below is the target paper to be reviewed, including both a text summary and screenshots of each page, and a concrete peer review of the paper.
    Your tasks is to convert the review feedback into a clear, actionable to-do list for the authors to address in their revision. Present each action in the Action:Objective[#location] format, and output as a BULLET POINT list.

    Paper summary:
    {text_summary}

    Peer Review:
    {rag_review}
    """

    todo_messages = [
        {"role": "system", "content": ACTION_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": todo_prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"}
        ]}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=todo_messages,
        temperature=0.3,
        max_tokens=4000
    )

    todo_list = [l.strip(" -*") for l in response.choices[0].message.content.splitlines() if l.strip().startswith(('-', '*'))]

    print(todo_list)
    status_placeholder.empty()

    print(f"[Status] Completed RAG review generation.")

    return reference_summary, rag_review, todo_list
