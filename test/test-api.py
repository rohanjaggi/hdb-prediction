import requests

def test_api():
    base_url = "http://0.0.0.0:8000"
    
    print("health test")
    health = requests.get(f"{base_url}/health")
    assert health.status_code == 200
    print("health ok")
    
    print("prediction test")
    test_data = {
        "storey_median": 10,
        "floor_area_sqm": 90,
        "remaining_lease": 99,
        "town": "ANG MO KIO",
        "flat_type": "4 ROOM"
    }

    edge_cases = [
        {"storey_median": 1, "floor_area_sqm": 30, "remaining_lease": 10, "town": "WOODLANDS", "flat_type": "2 ROOM"},
        {"storey_median": 25, "floor_area_sqm": 45, "remaining_lease": 30, "town": "CENTRAL", "flat_type": "1 ROOM"},
    ]

    for i, edge_case in enumerate(edge_cases, 1):
        try:
            response = requests.post(f"{base_url}/bto_price", json=edge_case)
            if response.status_code == 200:
                result = response.json()
                assert 50000 <= result <= 2000000
                print(f"Edge case {i}: ${result:,.0f}")
            else:
                print(f"Edge case {i}: HTTP {response.status_code} (expected for invalid data)")
        except Exception as e:
            print(f"Edge case {i} failed: {str(e)[:50]}")

    
    response = requests.post(f"{base_url}/bto_price", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert 100000 <= result <= 1000000 

    invalid_data = {"town": "INVALID", "flat_type": "INVALID"}
    error_response = requests.post(f"{base_url}/bto_price", json=invalid_data)
    assert error_response.status_code in [400, 422]
    print(error_response.status_code)

    print(f"prediction ok")
    
    print("api ok")
    # test can be more robust by checking more endpoints and responses thoroughly

if __name__ == "__main__":
    test_api()