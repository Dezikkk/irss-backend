curl -X 'POST' \
  'http://127.0.0.1:8000/starosta/submit' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "description": "huevo",
  "group_amount": 4,
  "max_students": [3, 4, 5, 6],
  "expiration_date": "2012-04-23T18:25:43.511Z",
  "password": "hello"
}' \
	> log.txt
