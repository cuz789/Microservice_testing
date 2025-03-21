import requests
import pytest
import time

BASE_URL_GATEWAY = "http://localhost:8000"

# Test user details from your provided payload
TEST_USER_ID = "d8fcddf1-f639-4b62-b0ae-c424efcbd4fe"
TEST_USER_EMAILS = ["kp@example.org"]
TEST_USER_ADDRESS = {
    "street": "500 Oak Avenue",
    "city": "Austin",
    "state": "TX",
    "postalCode": "73301",
    "country": "USA"
}
@pytest.fixture(scope="session")
def order_creation():
    """Create an order using the API Gateway endpoint for a predefined test user."""
    url = f"{BASE_URL_GATEWAY}/orders/"
    payload = {
        "userId": TEST_USER_ID,
        "items": [
            {"itemId": "item001", "quantity": 2, "price": 29.99},
            {"itemId": "item002", "quantity": 1, "price": 49.99}
        ],
        "userEmails": TEST_USER_EMAILS,
        "deliveryAddress": TEST_USER_ADDRESS,
        "orderStatus": "under process"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201, "Order creation failed"
    order_data = response.json()
    print(f"\n✅ Order created successfully! Order ID: {order_data['orderId']}")
    return order_data

def test_fetch_orders_by_status(order_creation):
    """
    Test that the created order is returned when fetching orders filtered by orderStatus.
    """
    status = order_creation["orderStatus"]
    get_url = f"{BASE_URL_GATEWAY}/orders?status={status}"
    
    # Retry mechanism to account for eventual consistency delays
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
    
    # Validate that the created order is present in the returned orders
    order_ids = [order.get("orderId") for order in orders_list]
    assert order_creation["orderId"] in order_ids, "Created order not found in orders returned by GET"
    
    print(f"\n📢 GET orders by status successful. Order ID {order_creation['orderId']} found in the response.")
