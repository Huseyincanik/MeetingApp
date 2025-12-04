import json
from typing import Dict
from openai import OpenAI
from ..config import settings


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    async def summarize_transcript(self, transcript_text: str, language: str = "tr") -> Dict:
        """Transkripti özetle"""
        lang_prompt = "Türkçe" if language == "tr" else "English"
        
        prompt = f"""Aşağıdaki toplantı transkriptini {lang_prompt} olarak özetle ve anahtar noktaları çıkar.

Transkript:
{transcript_text}

Lütfen şu formatta JSON yanıt ver:
{{
    "summary": "Toplantının genel özeti",
    "key_points": ["Anahtar nokta 1", "Anahtar nokta 2", "Anahtar nokta 3"]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant that summarizes meeting transcripts in {lang_prompt}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # JSON parse et
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Eğer JSON değilse, düz metin olarak işle
                result = {
                    "summary": content,
                    "key_points": []
                }
            
            return {
                "summary": result.get("summary", content),
                "key_points": json.dumps(result.get("key_points", []), ensure_ascii=False)
            }
        
        except Exception as e:
            raise Exception(f"OpenAI özetleme hatası: {str(e)}")

