import requests
import pytest

BASE_URL_GATEWAY = "http://localhost:8000"

@pytest.fixture(scope="session")
def user_creation():
    """Create a user using the API Gateway endpoint with a new payload."""
    url = f"{BASE_URL_GATEWAY}/users/"
    payload = {
        "firstName": "Ethan",
        "lastName": "Hunt",
        "emails": ["ethann.huntt@imf.org"],
        "deliveryAddress": {
            "street": "100 Spy Lane",
            "city": "Los Angeles",
            "state": "CA",
            "postalCode": "90001",
            "country": "USA"
        },
        "phoneNumber": "13235550199",
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    # Ensure user is created before returning the response
    assert response.status_code == 201, "User creation failed"

    return response.json()  # Returning JSON response to extract userId

def test_create_and_validate_user(user_creation):
    """Test user creation and validation via GET request."""
    
    # ✅ Capture details from the POST response
    user_id = user_creation["userId"]  
    first_name = user_creation["firstName"]
    last_name = user_creation["lastName"]
    emails = user_creation["emails"]

    # ✅ Perform GET request using the captured `userId`
    get_url = f"{BASE_URL_GATEWAY}/users/{user_id}"
    get_response = requests.get(get_url)

    # ✅ Validate GET response status code
    assert get_response.status_code == 200, "GET request failed or user not found"
    
    get_response_json = get_response.json()

    # ✅ Validate GET response data matches POST response data
    assert get_response_json["userId"] == user_id, "User ID mismatch"
    assert get_response_json["firstName"] == first_name, "First name mismatch"
    assert get_response_json["lastName"] == last_name, "Last name mismatch"
    assert get_response_json["emails"] == emails, "Emails mismatch"
