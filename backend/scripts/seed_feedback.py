import json
import urllib.request

feedbacks = [
    {
        "rating": 1,
        "reasons": ["bugs", "slow"],
        "comments": "The installer kept crashing, and it loaded extremely slowly.",
        "email": "dissatisfied_developer@gmail.com"
    },
    {
        "rating": 2,
        "reasons": ["hard_config"],
        "comments": "Could not get python dependencies to resolve properly on windows.",
        "email": "pytorch_user1@outlook.com"
    },
    {
        "rating": 3,
        "reasons": ["one_off", "other"],
        "comments": "Only needed it to check one environment structure, good tool though.",
        "email": None
    },
    {
        "rating": 4,
        "reasons": ["missing_hardware"],
        "comments": "No support for AMD ROCm profiling yet. Will check back when it is added.",
        "email": "amd_fanatic@yahoo.com"
    },
    {
        "rating": 5,
        "reasons": ["one_off"],
        "comments": "Nice tool, uninstalled after generating my script successfully.",
        "email": "ml_engineer@corp.com"
    },
    {
        "rating": 2,
        "reasons": ["unclear_docs", "hard_config"],
        "comments": "The CLI arguments weren't clearly documented in the getting started guide.",
        "email": None
    },
    {
        "rating": 4,
        "reasons": ["other"],
        "comments": "Decided to run standard manual conda env setup. App looks clean though.",
        "email": "coder_bob@gmail.com"
    },
    {
        "rating": 3,
        "reasons": ["slow"],
        "comments": "Took too long to fetch PyPI database.",
        "email": "speedy@gmail.com"
    }
]

url = "http://localhost:8000/api/v1/uninstall/feedback"

print("Seeding 8 feedback entries to local server...")

for idx, fb in enumerate(feedbacks):
    req = urllib.request.Request(
        url,
        data=json.dumps(fb).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode('utf-8'))
            print(f"[{idx+1}] Success! Stored feedback ID: {response_data['id']}")
    except Exception as e:
        print(f"[{idx+1}] Failed to seed: {e}")
