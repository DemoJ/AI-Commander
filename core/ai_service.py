import json
from openai import OpenAI
from utils.config import ConfigManager

class AIService:
    def __init__(self, config: ConfigManager):
        self.config = config

    def generate_commands(self, input_files, user_requirement):
        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url")
        model = self.config.get("model_name")

        if not api_key:
            raise ValueError("API Key is missing. Please configure it in Settings.")

        client = OpenAI(api_key=api_key, base_url=base_url)

        system_prompt = (
            "You are an FFmpeg expert. Please translate the user's natural language requirement "
            "and input file path(s) into a JSON object containing the FFmpeg command-line arguments.\n"
            "The output must be a pure JSON object with a single key 'commands', which is a list of lists of strings.\n"
            "Example 1 (Batch processing): {\"commands\": [[\"-i\", \"file1.mp4\", \"out1.mp4\"], [\"-i\", \"file2.mp4\", \"out2.mp4\"]]}\n"
            "Example 2 (Merge/Complex): {\"commands\": [[\"-i\", \"file1.mp4\", \"-i\", \"file2.mp4\", \"merged.mp4\"]]}\n"
            "Do not include the 'ffmpeg' command itself at the beginning of the arguments.\n"
            "Do not include Markdown formatting or any other text.\n"
            "Ensure the output file path is valid and derived from the input path if not specified."
        )

        user_content = f"Input Files: {input_files}\nRequirement: {user_requirement}"

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1
            )

            content = response.choices[0].message.content.strip()
            
            # Clean up potential markdown code blocks if the model disobeys
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()

            data = json.loads(content)
            if not isinstance(data, dict) or "commands" not in data or not isinstance(data["commands"], list):
                raise ValueError("AI returned valid JSON but not the expected structure ({\"commands\": [[args...], ...]}).")
            
            return data["commands"]

        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse AI response as JSON:\n{content}")
        except Exception as e:
            raise e
