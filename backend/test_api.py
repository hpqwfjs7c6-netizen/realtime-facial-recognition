import requests
import time

# 1x1 transparent PNG in base64
base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="

time.sleep(2) # wait for server to start

try:
    response = requests.post(
        "http://localhost:8001/analyze-face",
        json={"image": base64_image}
    )
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
except Exception as e:
    print("ERROR:", str(e))
