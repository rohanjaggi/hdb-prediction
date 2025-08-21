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
    
    response = requests.post(f"{base_url}/bto_price", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert 200000 <= result <= 1000000
    print(f"prediction ok")
    
    print("api ok")
    # test can be more robust by checking more endpoints and responses thoroughly

if __name__ == "__main__":
    test_api()