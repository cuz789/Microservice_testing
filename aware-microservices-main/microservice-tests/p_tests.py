import requests

BASE_URL_GATEWAY = "http://localhost:8000"

def create_users():
    """Create 10 users using the API Gateway endpoint with unique emails."""
    url = f"{BASE_URL_GATEWAY}/users/"
    headers = {"Content-Type": "application/json"}


    for i in range(10):
        payload = {
            "firstName": "Ethan",
            "lastName": "Hunt",
            "emails": [f"ethan.hunt{i}@imf.org"],
            "deliveryAddress": {
                "street": "100 Spy Lane",
                "city": "Los Angeles",
                "state": "CA",
                "postalCode": "90001",
                "country": "USA"
            },
            "phoneNumber": "13235550199",
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 201:
            print(f"User {i+1} created with email ethan.hunt{i}@imf.org")
        else:
            print(f"Failed to create user {i+1}. Status Code: {response.status_code}, Response: {response.text}")

if __name__ == "__main__":
    create_users()
