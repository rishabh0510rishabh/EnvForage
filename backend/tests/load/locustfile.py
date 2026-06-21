from locust import HttpUser, between, task


class TroubleshootUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def troubleshoot_stream(self):
        payload = {
            "diagnostic": {
                "agent_version": "2.0.0",
                "os": {
                    "name": "Ubuntu 22.04",
                    "version": "22.04",
                    "architecture": "x86_64",
                },
                "cpu": {
                    "brand": "Intel i9-13900K",
                    "cores": 24,
                    "threads": 32,
                },
                "ram": {
                    "total_gb": 64,
                    "available_gb": 48,
                },
                "gpus": [
                    {
                        "name": "RTX 4090",
                        "vram_gb": 24,
                        "driver_version": "535.129",
                    }
                ],
                "cuda": {
                    "version": "11.8",
                    "toolkit_path": "/usr/local/cuda",
                },
            },
            "profile_slug": "pytorch-cuda",
            "user_description": ("CUDA 11.8 incompatible with PyTorch 2.3"),
        }

        with self.client.post(
            "/api/v1/troubleshoot",
            json=payload,
            stream=True,
            catch_response=True,
        ) as response:
            chunk_count = 0

            try:
                for line in response.iter_lines():
                    if line:
                        chunk_count += 1

                if chunk_count == 0:
                    response.failure("No SSE chunks received")
                else:
                    response.success()

            except Exception as exc:
                response.failure(f"Streaming error: {exc}")
