import requests
import pytest
import time

BASE_URL_GATEWAY = "http://localhost:8000"

# Provided test user details
TEST_USER_ID = "302015c6-ea2b-46f5-a192-070ea07542f9"

@pytest.fixture(scope="session")
def create_order_for_user():
    """Create an order for the predefined test user."""
    url = f"{BASE_URL_GATEWAY}/orders/"
    payload = {
        "userId": TEST_USER_ID,
        "items": [
            {"itemId": "item001", "quantity": 2, "price": 29.99},
            {"itemId": "item002", "quantity": 1, "price": 49.99}
        ],
        "userEmails": ["kp@example.org"],
        "deliveryAddress": {
            "street": "500 Oak Avenue",
            "city": "Austin",
            "state": "TX",
            "postalCode": "73301",
            "country": "USA"
        },
        "orderStatus": "under process"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, "Order creation failed"
    order_data = response.json()
    print(f"\n✅ Order created successfully! Order ID: {order_data['orderId']}")
    return order_data

def test_validate_event_driven_user_update_propagation(create_order_for_user):
    """
    Test Case 3: Validate Event-Driven User Update Propagation.
    
    Objective:
    Ensure that when a user's email or delivery address is updated via a PUT request,
    an event is triggered that updates all linked orders.
    This test updates the user and then checks that the corresponding order reflects 
    the updated emails and delivery address.
    """
    # New user data for update
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
    
    # Update the user via PUT /users/{userId}
    user_update_url = f"{BASE_URL_GATEWAY}/users/{TEST_USER_ID}"
    headers = {"Content-Type": "application/json"}
    update_response = requests.put(user_update_url, json=updated_user_payload, headers=headers)
    assert update_response.status_code == 200, "User update failed"
    
    updated_user_data = update_response.json()
    # Check if the response is a list and get the first element if so
    if isinstance(updated_user_data, list):
        updated_user = updated_user_data[0]
    else:
        updated_user = updated_user_data

    print(f"\n✅ User updated successfully! New emails: {updated_user['emails']}")
    
    # Wait for the event-driven synchronization to propagate the update
    time.sleep(5)  # Adjust delay as necessary based on system response
    
    # Retrieve orders with status 'under process'
    get_url = f"{BASE_URL_GATEWAY}/orders?status=under process"
    retries = 5
    order_found = False
    for attempt in range(retries):
        response = requests.get(get_url)
        if response.status_code == 200:
            orders = response.json()
            for order in orders:
                if order.get("orderId") == create_order_for_user["orderId"]:
                    order_found = True
                    # Validate that the order's userEmails and deliveryAddress have been updated
                    assert order.get("userEmails") == updated_user_payload["emails"], "User emails not updated in order"
                    assert order.get("deliveryAddress") == updated_user_payload["deliveryAddress"], "Delivery address not updated in order"
                    print(f"\n📢 Order {order['orderId']} updated successfully with new user data.")
                    break
            if order_found:
                break
        print(f"Attempt {attempt+1}: Order update not propagated yet. Retrying in 2s...")
        time.sleep(2)
    
    assert order_found, "Updated order not found after user update propagation"
