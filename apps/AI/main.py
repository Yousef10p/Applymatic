import os
from groq import Groq

class ApplymaticAI:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing from your environment variables.")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"

    def generate_cover_letter(self, resume_text, include_company=True):
        if include_company:
            company_rule = "1. Use the exact text '{company_name}' as a placeholder for the target company (do not invent a company)."
        else:
            company_rule = "1. Write a universally generic cover letter. DO NOT mention any specific company name and DO NOT use any placeholders like '{company_name}'."

        prompt = f"""
        You are an elite career coach. Based on the following resume, write a professional, confident, and concise cover letter. 
        CRITICAL RULES:
        {company_rule}
        2. Keep it under 250 words. 
        3. Do NOT include placeholder addresses at the top. Just start directly with 'Dear Hiring Manager,' and end with a professional closing.
        
        RESUME:
        {resume_text}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def refine_cover_letter(self, current_text, include_company=True):
        if include_company:
            company_rule = "1. Keep the '{company_name}' placeholder intact if it exists. If it is missing, seamlessly add '{company_name}' into the opening paragraph."
        else:
            company_rule = "1. Make the cover letter completely generic. Remove ANY specific company names and absolutely REMOVE the '{company_name}' placeholder if it is in the text."

        prompt = f"""
        You are an expert copywriter. Please refine and polish the following cover letter. 
        Fix any grammatical errors, improve the flow, and make it sound highly professional and persuasive.
        CRITICAL RULES:
        {company_rule}
        2. Do not add unnecessary addresses or dates at the top.
        3. avoid this type of things 'Here's a refined and polished version of the cover letter'
        
        CURRENT COVER LETTER:
        {current_text}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()