import requests, os
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get('AZURE_FACE_KEY')
endpoint = os.environ.get('AZURE_FACE_ENDPOINT')

img_data = requests.get('https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/Face/images/Family1-Dad1.jpg').content

url = f"{endpoint.rstrip('/')}/face/v1.0/detect?detectionModel=detection_01&recognitionModel=recognition_04&returnFaceAttributes=emotion"
headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Content-Type': 'application/octet-stream'
}

response = requests.post(url, headers=headers, data=img_data)
print('STATUS:', response.status_code)
print('BODY:', response.text)
