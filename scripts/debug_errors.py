"""Debug which rows error and why."""
import asyncio
import csv
import httpx

TEMPLATE = (
    "[INST] Task: Check if there is unsafe content in the User message.\n"
    "<BEGIN UNSAFE CONTENT CATEGORIES>\nO1: Violence and Hate.\nO2: Sexual Content.\nO3: Criminal Planning.\n"
    "O4: Guns and Illegal Weapons.\nO5: Regulated or Controlled Substances.\nO6: Self-Harm.\n"
    "<END UNSAFE CONTENT CATEGORIES>\n<BEGIN CONVERSATION>\nUser: {text}\n<END CONVERSATION>\n"
    "- First line must read safe or unsafe. [/INST]"
)


async def test_one(client: httpx.AsyncClient, i: int, text: str) -> None:
    try:
        r = await client.post(
            "/v1/chat/completions",
            json={
                "model": "llamaguard-7b",
                "messages": [{"role": "user", "content": TEMPLATE.format(text=text[:1200])}],
                "temperature": 0.0,
                "max_tokens": 32,
            },
        )
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        print(f"row {i}: HTTP {r.status_code}, content={content!r}")
    except Exception as e:
        import traceback
        print(f"row {i}: EXCEPTION {type(e).__name__}: {e}")
        traceback.print_exc()


async def main() -> None:
    rows = list(csv.DictReader(open("data/smoke_sample_50.csv", encoding="utf-8-sig")))
    error_ids = {7, 8, 22, 25, 37}

    async with httpx.AsyncClient(base_url="http://127.0.0.1:1234", timeout=30) as client:
        for i, row in enumerate(rows):
            if i in error_ids:
                print(f"\n--- row {i} (len={len(row['text'])}) ---")
                await test_one(client, i, row["text"])


if __name__ == "__main__":
    asyncio.run(main())
