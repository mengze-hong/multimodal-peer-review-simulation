import json
import re 

def build_summary_prompt(paper_title: str, reviews: list[str]):
    joined = "\n\n---\n\n".join(reviews[:2])
    return f"""
You are an advanced AI persona acting as a seasoned reviewer for academic venues, possessing extensive experience in synthesizing academic feedback and providing constructive criticism. Your are tasked with summarizing existing reviews to guide junior reviewers in crafting high-quality reviews for new submissions.

**Context:**
Paper Title: {paper_title}

**Background:**
Your goal is to extract insights from these reviews regarding REVIEW PRACTICES, emphasize on the focal point of review writing, the structure, and the quality standard. This will be used to guide the generation of future reviews for similar papers submitted to this venue.

**Reviews for Reference:**
{joined}

**Task:**
Construct a concise **reference review** based on the provided reviews, adhering to the following structured format:
- **Weaknesses:** Identify and articulate the principal weaknesses in general aspects, avoiding specific details tied to the paper itself but focus on the review practices, such as criticizing clarity, methodology, experimental design, and presentation.
- **Improvements:** Summarize an array of improvement TYPES that reviewers often mention, such as experimental validation, theoretical grounding, clarity of exposition, and relevance to the field. Be specific, as this will serve as guidence for future reviewer to refer and react.

**Output Requirements:**
Return the summary in JSON format with the following structure:
{{
  "weaknesses": [ ... ],
  "improvements": [ ... ],
}}
"""


def summarise_reference(client, title: str, reviews: list[str]):
    prompt = build_summary_prompt(title, reviews)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You must return only valid JSON following the specified schema. No explanations, no Markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        raw_output = resp.choices[0].message.content.strip()

        # === Clean markdown fences if present ===
        cleaned_output = re.sub(r"^```json\s*|\s*```$", "", raw_output.strip())

        # === Try parsing JSON safely ===
        try:
            parsed = json.loads(cleaned_output)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            print("Model output looked like JSON but failed to parse. Dumping cleaned version:")
            print(cleaned_output[:500])
            return json.dumps({"raw_text": cleaned_output}, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"summarise_reference() failed: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)