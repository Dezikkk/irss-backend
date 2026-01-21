curl -X 'POST' \
  'http://127.0.0.1:8000/student/priorities' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "token": "string",
  "email": "user@example.com",
  "preferences": [
    0
  ],
  "password": "string"
}' \
	> log.txt
