import os
import re

FILES = [
    r"D:\pantrymind-desktop\services\finance_chat_service.py",
    r"D:\pantrymind-desktop\services\kitchen_chat_service.py",
    r"D:\pantrymind-desktop\services\smart_expiry_agent.py"
]

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add import if missing
    if "call_gemini_with_retry" not in content:
        # Insert after the first import or datetime
        if "from google.genai import types" in content:
            content = content.replace(
                "from google.genai import types",
                "from google.genai import types\nfrom services.llm_client import call_gemini_with_retry"
            )
        elif "import os" in content:
            content = content.replace(
                "import os",
                "import os\nfrom services.llm_client import call_gemini_with_retry"
            )
    
    # 1. self.gemini.aio.models.generate_content
    # Find block:
    # response = await self.gemini.aio.models.generate_content(
    #     model=self.model,
    #     contents=contents,
    #     config=config,
    # )
    content = content.replace(
        "        response = await self.gemini.aio.models.generate_content(\n            model=self.model,\n            contents=contents,\n            config=config,\n        )",
        "        response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(\n            model=self.model,\n            contents=contents,\n            config=config,\n        ))"
    )

    content = content.replace(
        "            response = await self.gemini.aio.models.generate_content(\n                model=self.model,\n                contents=contents,\n                config=config,\n            )",
        "            response = await call_gemini_with_retry(lambda: self.gemini.aio.models.generate_content(\n                model=self.model,\n                contents=contents,\n                config=config,\n            ))"
    )

    # 2. smart_expiry_agent.py
    # response = await gemini_client.aio.models.generate_content(
    #     model=model_name,
    #     contents=prompt,
    #     config=genai_types.GenerateContentConfig(
    #         response_mime_type="application/json",
    #         temperature=0.15,
    #     )
    # )
    content = content.replace(
        "        response = await gemini_client.aio.models.generate_content(\n            model=model_name,\n            contents=prompt,\n            config=genai_types.GenerateContentConfig(\n                response_mime_type=\"application/json\",\n                temperature=0.15,\n            )\n        )",
        "        response = await call_gemini_with_retry(lambda: gemini_client.aio.models.generate_content(\n            model=model_name,\n            contents=prompt,\n            config=genai_types.GenerateContentConfig(\n                response_mime_type=\"application/json\",\n                temperature=0.15,\n            )\n        ))"
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for file in FILES:
    patch_file(file)

print("Patch complete")
