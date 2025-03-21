import requests
import pytest
import time

BASE_URL_GATEWAY = "http://localhost:8000"

# Fixture to create a user and share its details with all tests.
@pytest.fixture(scope="session")
def created_user():
    """Create a user and return its details."""
    url = f"{BASE_URL_GATEWAY}/users/"
    payload = {
        "firstName": "Ethan",
        "lastName": "Hunt",
        "emails": ["ethann.hunt@imf.org"],
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
    assert response.status_code == 201, "User creation failed"
    return response.json()

def test_create_and_validate_user(created_user):
    """Test creation of a user and validation via GET request."""
    user_id = created_user["userId"]
    first_name = created_user["firstName"]
    last_name = created_user["lastName"]
    emails = created_user["emails"]
    
    # Perform GET request to validate the created user.
    get_url = f"{BASE_URL_GATEWAY}/users/{user_id}"
    get_response = requests.get(get_url)
    assert get_response.status_code == 200, "GET request failed or user not found"
    
    get_response_json = get_response.json()
    assert get_response_json["userId"] == user_id, "User ID mismatch"
    assert get_response_json["firstName"] == first_name, "First name mismatch"
    assert get_response_json["lastName"] == last_name, "Last name mismatch"
    assert get_response_json["emails"] == emails, "Emails mismatch"

# Fixture to create an order using the created user.
@pytest.fixture(scope="session")
def created_order(created_user):
    """Create an order using the details of the created user."""
    user_id = created_user["userId"]
    payload = {
        "userId": user_id,
        "items": [
            {"itemId": "item001", "quantity": 2, "price": 29.99},
            {"itemId": "item002", "quantity": 1, "price": 49.99}
        ],
        # Using the user's emails and deliveryAddress from the created user.
        "userEmails": created_user["emails"],
        "deliveryAddress": created_user["deliveryAddress"],
        "orderStatus": "under process"
    }
    headers = {"Content-Type": "application/json"}
    url = f"{BASE_URL_GATEWAY}/orders/"
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, "Order creation failed"
    order_data = response.json()
    print(f"\n✅ Order created successfully! Order ID: {order_data['orderId']}")
    return order_data

def test_fetch_orders_by_status(created_order):
    """
    Test that the created order is returned when fetching orders filtered by orderStatus.
    """
    status = created_order["orderStatus"]
    get_url = f"{BASE_URL_GATEWAY}/orders?status={status}"
    
    # Retry mechanism to account for eventual consistency delays.
    retries = 5
    for attempt in range(retries):
        response = requests.get(get_url)
        if response.status_code == 200:
            break
        print(f"Attempt {attempt+1}: GET orders by status returned {response.status_code}. Retrying in 2s...")
        time.sleep(2)
    assert response.status_code == 200, f"GET orders by status failed after {retries} retries"
    
    orders_list = response.json()
    assert isinstance(orders_list, list), "Expected GET response to be a list"
    
    # Validate that the created order is present in the returned orders.
    order_ids = [order.get("orderId") for order in orders_list]
    assert created_order["orderId"] in order_ids, "Created order not found in orders returned by GET"
    print(f"\n📢 GET orders by status successful. Order ID {created_order['orderId']} found in the response.")

def test_validate_event_driven_user_update_propagation(created_user, created_order):
    """
    Test Case: Validate that when a user's email or delivery address is updated,
    an event is triggered that updates all linked orders.
    """
    updated_user_payload = {
        "emails": ["new.email@example.org", "additional.email@example.org"],
        "deliveryAddress": {
            "street": "123 New Street",
            "city": "New City",
            "state": "NC",
            "postalCode": "27001",
            "country": "USA"
        }
    }
    
    # Update the user via PUT /users/{userId}.
    user_id = created_user["userId"]
    user_update_url = f"{BASE_URL_GATEWAY}/users/{user_id}"
    headers = {"Content-Type": "application/json"}
    update_response = requests.put(user_update_url, json=updated_user_payload, headers=headers)
    assert update_response.status_code == 200, "User update failed"
    
    updated_user_data = update_response.json()
    # If the response is a list, take the first element.
    if isinstance(updated_user_data, list):
        updated_user = updated_user_data[0]
    else:
        updated_user = updated_user_data

    print(f"\n✅ User updated successfully! New emails: {updated_user['emails']}")
    
    # Wait for the event-driven synchronization to propagate the update.
    time.sleep(5)  # Adjust the delay as necessary.
    
    # Retrieve orders with status 'under process'.
    get_url = f"{BASE_URL_GATEWAY}/orders?status=under process"
    retries = 5
    order_found = False
    for attempt in range(retries):
        response = requests.get(get_url)
        if response.status_code == 200:
            orders = response.json()
            for order in orders:
                if order.get("orderId") == created_order["orderId"]:
                    order_found = True
                    # Validate that the order's userEmails and deliveryAddress have been updated.
                    assert order.get("userEmails") == updated_user_payload["emails"], "User emails not updated in order"
                    assert order.get("deliveryAddress") == updated_user_payload["deliveryAddress"], "Delivery address not updated in order"
                    print(f"\n📢 Order {order['orderId']} updated successfully with new user data.")
                    break
            if order_found:
                break
        print(f"Attempt {attempt+1}: Order update not propagated yet. Retrying in 2s...")
        time.sleep(2)
    
    assert order_found, "Updated order not found after user update propagation"
